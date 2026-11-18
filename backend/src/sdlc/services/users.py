"""DB-backed accounts + sessions.

Thin async layer over ``AppUser``/``UserSession``, in the same shape as
``services.conversations``: explicit ``AsyncSession`` in, plain data or ORM
rows out, no HTTP concepts. ``api/auth.py`` owns the cookie + status codes.

The only non-obvious rule here is that a session token is *never* stored or
looked up in plaintext — see ``sdlc.core.security.hash_token``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sdlc.core.security import hash_password, hash_token, new_session_token
from sdlc.db.models import AppUser, UserSession

logger = logging.getLogger(__name__)

#: A token whose last_seen_at is younger than this is not touched again. The
#: chat stream issues many requests per turn; without it every one of them
#: would be an UPDATE, on a row nothing reads.
_LAST_SEEN_REFRESH = timedelta(hours=1)


class EmailTaken(Exception):
    """Registration hit the case-insensitive unique index on email."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalise_email(email: str) -> str:
    """Trim + lowercase. Applied on both write and lookup paths."""
    return email.strip().lower()


# ── Users ───────────────────────────────────────────────────────────────


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str = "",
) -> AppUser:
    """Insert an account, raising :class:`EmailTaken` if the email is in use."""
    user = AppUser(
        email=normalise_email(email),
        password_hash=hash_password(password),
        display_name=display_name.strip(),
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise EmailTaken(f"An account already exists for {email!r}") from exc
    return user


async def get_user_by_email(session: AsyncSession, email: str) -> AppUser | None:
    stmt = select(AppUser).where(func.lower(AppUser.email) == normalise_email(email))
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_user(session: AsyncSession, user_id: int) -> AppUser | None:
    return await session.get(AppUser, user_id)


async def set_password(session: AsyncSession, user: AppUser, password: str) -> None:
    """Rehash in place. Does not touch sessions — the caller decides."""
    user.password_hash = hash_password(password)
    await session.flush()


# ── Sessions ────────────────────────────────────────────────────────────


async def create_session(
    session: AsyncSession,
    *,
    user: AppUser,
    ttl_days: int,
    user_agent: str = "",
    ip: str = "",
) -> str:
    """Mint a session and return the plaintext token.

    That return value is the only place the plaintext ever exists — it goes
    straight into the response cookie, and the row keeps only its digest.
    """
    token, token_hash = new_session_token()
    now = _utc_now()
    session.add(
        UserSession(
            token_hash=token_hash,
            user_id=user.id,
            created_at=now,
            expires_at=now + timedelta(days=ttl_days),
            last_seen_at=now,
            user_agent=(user_agent or "")[:200],
            ip=(ip or "")[:64],
        )
    )
    await session.flush()
    return token


async def resolve_session(session: AsyncSession, token: str) -> AppUser | None:
    """Return the active user behind a token, or None.

    Filters on both ``expires_at`` and ``is_active`` so deactivating an
    account is an immediate logout everywhere, without hunting tokens down.
    """
    if not token:
        return None
    token_hash = hash_token(token)
    stmt = (
        select(UserSession, AppUser)
        .join(AppUser, AppUser.id == UserSession.user_id)
        .where(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > _utc_now(),
            AppUser.is_active.is_(True),
        )
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        return None
    session_row, user = row
    now = _utc_now()
    last_seen = session_row.last_seen_at
    # A naive timestamp means something wrote it outside the ORM path; treat
    # it as stale instead of guessing an offset and skipping the refresh.
    if last_seen is None or last_seen.tzinfo is None or now - last_seen > _LAST_SEEN_REFRESH:
        session_row.last_seen_at = now
        await session.flush()
    return user


async def revoke_session(session: AsyncSession, token: str) -> bool:
    """Delete one session by its plaintext token. True if a row was removed."""
    if not token:
        return False
    result = await session.execute(
        delete(UserSession).where(UserSession.token_hash == hash_token(token))
    )
    await session.flush()
    return bool(result.rowcount)


async def revoke_user_sessions(
    session: AsyncSession,
    user_id: int,
    *,
    except_token_hash: str | None = None,
) -> int:
    """Drop every session for a user, optionally sparing the current one."""
    stmt = delete(UserSession).where(UserSession.user_id == user_id)
    if except_token_hash:
        stmt = stmt.where(UserSession.token_hash != except_token_hash)
    result = await session.execute(stmt)
    await session.flush()
    return int(result.rowcount or 0)


async def delete_expired_sessions(session: AsyncSession) -> int:
    """Sweep expired rows. Cheap, so it runs on every successful login."""
    result = await session.execute(
        delete(UserSession).where(UserSession.expires_at <= _utc_now())
    )
    await session.flush()
    return int(result.rowcount or 0)
