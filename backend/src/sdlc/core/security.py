"""Password hashing, session tokens and login throttling.

Deliberately stdlib-only: ``hashlib.scrypt`` is memory-hard and already
available, so adding an account system does not add a supply-chain dependency
to a lockfile this project keeps deliberately thin. No JWT either — sessions
are opaque random tokens stored (hashed) in Postgres, so revocation is a
DELETE and there is no signing key to rotate.

Two files own auth, on purpose:

* this module — pure functions, no I/O, trivially testable;
* ``sdlc.services.users`` — the DB side.

Nothing here logs, and nothing here returns a password or token to a caller
that shouldn't see it.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from collections import deque

# ── Passwords ──────────────────────────────────────────────────────────

# scrypt cost. Memory = 128 * n * r = 16 MiB at these values, which is the
# point: a GPU cracker that could try billions of SHA-256 guesses per second
# gets a few thousand here. Parameters are written INTO the stored string so
# they can be raised later without invalidating existing hashes — an old row
# keeps verifying with the parameters it was created with.
_SCRYPT_N = 16384  # 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32
# OpenSSL's default cap is 32 MiB; be explicit rather than depend on it.
_SCRYPT_MAXMEM = 64 * 1024 * 1024
_SALT_BYTES = 16
_ALGO = "scrypt"


def _b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def hash_password(password: str) -> str:
    """Hash a password into ``scrypt$n$r$p$salt_b64$hash_b64``."""
    salt = secrets.token_bytes(_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
        maxmem=_SCRYPT_MAXMEM,
    )
    return "$".join(
        (_ALGO, str(_SCRYPT_N), str(_SCRYPT_R), str(_SCRYPT_P), _b64e(salt), _b64e(derived))
    )


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash.

    Returns False — never raises — for a malformed hash, so a corrupted row
    is a failed login rather than a 500.
    """
    try:
        algo, n_s, r_s, p_s, salt_b64, hash_b64 = stored.split("$")
        if algo != _ALGO:
            return False
        salt = _b64d(salt_b64)
        expected = _b64d(hash_b64)
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n_s),
            r=int(r_s),
            p=int(p_s),
            dklen=len(expected),
            maxmem=_SCRYPT_MAXMEM,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derived, expected)


# Hashing a throwaway string on the user-not-found path keeps "unknown email"
# and "wrong password" the same wall time. Without it the 401 arrives
# measurably faster for an address that has no account, which turns the login
# form into an account-existence oracle.
DUMMY_HASH = hash_password("not-a-real-password-only-for-timing")


def burn_password_time(password: str) -> None:
    """Spend the same work a real verification would, then discard it."""
    verify_password(password, DUMMY_HASH)


# ── Session tokens ─────────────────────────────────────────────────────


def new_session_token() -> tuple[str, str]:
    """Return ``(plaintext_token, sha256_hex)``.

    The plaintext goes to the browser cookie exactly once; only the digest is
    stored, so a database dump cannot be replayed as a login.
    """
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    """Digest a session token for storage/lookup. Stable, so it is also the PK."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ── Login throttle ─────────────────────────────────────────────────────


class TooManyAttempts(Exception):
    """Raised when a login key has used up its window."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Too many login attempts; retry in {retry_after}s")
        self.retry_after = retry_after


class LoginThrottle:
    """In-process sliding-window counter keyed by an arbitrary string.

    # ponytail: in-process throttle; move to Redis if workers > 1. The
    # --prod gunicorn mode already runs one process per worker, so this
    # bounds attempts per process, not per deployment — same caveat as the
    # module-level run state.
    """

    #: Hard cap on tracked keys. A public login endpoint is an unbounded
    #: source of distinct keys (attacker picks the email), so eviction is what
    #: keeps this from being a memory DoS.
    MAX_KEYS = 5000

    def __init__(self, *, max_attempts: int, window_seconds: float) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._locks: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _trim(self, key: str, now: float) -> deque[float]:
        hits = self._locks.get(key)
        if hits is None:
            return deque()
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        return hits

    def check(self, key: str) -> None:
        """Raise :class:`TooManyAttempts` if ``key`` is saturated."""
        now = time.monotonic()
        with self._lock:
            hits = self._trim(key, now)
            if len(hits) < self.max_attempts:
                return
            retry_after = max(1, int(self.window_seconds - (now - hits[0])) + 1)
        raise TooManyAttempts(retry_after)

    def fail(self, key: str) -> None:
        """Record one failed attempt for ``key``."""
        now = time.monotonic()
        with self._lock:
            hits = self._trim(key, now)
            hits.append(now)
            self._locks[key] = hits
            while len(self._locks) > self.MAX_KEYS:
                # Insertion order, not LRU: a spammer cycling keys evicts the
                # oldest first, which is the cheapest thing that stays bounded.
                self._locks.pop(next(iter(self._locks)), None)

    def reset(self, key: str) -> None:
        """Clear a key after a successful login."""
        with self._lock:
            self._locks.pop(key, None)
