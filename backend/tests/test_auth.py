"""Auth: hashing, the login throttle, and the cookie gate.

Two halves, on purpose:

* **Pure functions** (sdlc.core.security, the ownership helper) always run —
  no database, no Docker, no network.
* **Endpoint tests** build a throwaway Postgres database, create the auth
  tables in it, and point the app's session factory at it. If no Postgres is
  reachable the DB half skips rather than failing: the rest of the suite is
  hermetic and this must not turn a missing local service into a red build.

The DB half is the part that actually proves the requirement — that a
conversation belongs to exactly one account — so it runs whenever it can.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import sdlc.api.app as app_module
from sdlc.api import auth as auth_module
from sdlc.core import security
from sdlc.core.security import LoginThrottle, TooManyAttempts

_DATABASE_URL = (
    os.getenv("TEST_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or "postgresql+asyncpg://postgres:password@localhost:5432/harness"
)

# One event loop for the whole module. A fresh asyncio.run() per test would
# hand the shared engine a different loop each time, which asyncpg rejects
# ("another operation is in progress" / "Event loop is closed") because the
# pooled connections belong to the loop that opened them.
_LOOP: asyncio.AbstractEventLoop | None = None


def _run(coro):
    global _LOOP
    if _LOOP is None or _LOOP.is_closed():
        _LOOP = asyncio.new_event_loop()
    return _LOOP.run_until_complete(coro)


@pytest.fixture(scope="module", autouse=True)
def _shared_event_loop():
    yield
    global _LOOP
    if _LOOP is not None:
        _LOOP.close()
        _LOOP = None


# ── Pure functions ──────────────────────────────────────────────────────


def test_password_hash_roundtrips_and_encodes_its_parameters():
    """The hash must carry its own cost parameters.

    Otherwise raising the scrypt cost later silently breaks every stored
    password, which is the classic way an auth migration becomes a reset.
    """
    stored = security.hash_password("correct horse battery staple")
    algorithm, n, r, p, salt, digest = stored.split("$")
    assert algorithm == "scrypt"
    assert (int(n), int(r), int(p)) == (16384, 8, 1)
    assert salt and digest
    assert security.verify_password("correct horse battery staple", stored)
    assert not security.verify_password("Correct horse battery staple", stored)


def test_salt_makes_identical_passwords_hash_differently():
    a = security.hash_password("same-password-here")
    b = security.hash_password("same-password-here")
    assert a != b
    assert security.verify_password("same-password-here", a)
    assert security.verify_password("same-password-here", b)


@pytest.mark.parametrize(
    "stored",
    ["", "garbage", "scrypt$x$y$z$q$w", "bcrypt$16384$8$1$AAAA$BBBB", "scrypt$0$0$0"],
)
def test_verify_password_rejects_malformed_hashes(stored: str):
    """A corrupted row is a failed login, never a 500."""
    assert security.verify_password("anything", stored) is False


def test_dummy_hash_is_a_real_number_of_bytes():
    """The not-found path must cost one real verification, not a short-circuit."""
    assert security.DUMMY_HASH.startswith("scrypt$")
    assert security.verify_password("guess", security.DUMMY_HASH) is False


def test_session_tokens_are_opaque_and_only_the_digest_is_stable():
    token, digest = security.new_session_token()
    assert len(token) >= 40
    assert digest == security.hash_token(token)
    assert digest != token
    assert security.new_session_token()[0] != token


def test_throttle_latches_and_recovers_after_the_window():
    throttle = LoginThrottle(max_attempts=3, window_seconds=60)
    for _ in range(3):
        throttle.fail("a@x.com|127.0.0.1")
    with pytest.raises(TooManyAttempts) as excinfo:
        throttle.check("a@x.com|127.0.0.1")
    assert 1 <= excinfo.value.retry_after <= 61
    # Another key (or a successful login) is unaffected.
    throttle.check("b@x.com|127.0.0.1")
    throttle.reset("a@x.com|127.0.0.1")
    throttle.check("a@x.com|127.0.0.1")


def test_throttle_evicts_keys_instead_of_growing_forever():
    """A public login form lets an attacker choose the key, so the map is bounded."""
    throttle = LoginThrottle(max_attempts=1, window_seconds=60)
    throttle.MAX_KEYS = 10
    for i in range(50):
        throttle.fail(f"user{i}@x.com|127.0.0.1")
    assert len(throttle._locks) <= 10


def test_registration_validates_shape_without_composition_rules():
    """Length only: passphrases are good, "Passw0rd!" is not."""

    def _check(email: str, password: str) -> None:
        auth_module._validate_registration(
            auth_module.RegisterRequest(email=email, password=password)
        )

    _check("someone@example.com", "a long enough passphrase")

    with pytest.raises(auth_module.HTTPException) as excinfo:
        _check("not-an-email", "a long enough passphrase")
    assert "email" in str(excinfo.value.detail).lower()

    with pytest.raises(auth_module.HTTPException) as excinfo:
        _check("someone@example.com", "short")
    assert "characters" in str(excinfo.value.detail)


# ── Ownership helper (no database needed) ───────────────────────────────


class _FakeConv:
    def __init__(self, user_id: int | None) -> None:
        self.user_id = user_id


def test_ownership_404s_for_another_users_row_and_for_legacy_rows():
    """Both cases must look identical from outside.

    A 403 for "exists but not yours" and 404 for "missing" would tell an
    attacker which conversation ids are real. The NULL case is the legacy one:
    those rows are unreachable by design and are never re-assigned.
    """
    me = auth_module.CurrentUser(id=7, email="me@example.com")
    assert app_module._assert_owns(_FakeConv(7), me).user_id == 7
    for foreign in (_FakeConv(8), _FakeConv(None), None):
        with pytest.raises(auth_module.HTTPException) as excinfo:
            app_module._assert_owns(foreign, me)
        assert excinfo.value.status_code == 404


def _patch_ownership(monkeypatch: pytest.MonkeyPatch, conv: object) -> None:
    """Make _owned_conversation see *conv* without touching a database."""

    class _Session:
        async def __aenter__(self) -> "_Session":
            return self

        async def __aexit__(self, *exc: object) -> None:
            return None

    async def _get_conversation(_session: object, thread_id: str) -> object:
        return conv

    monkeypatch.setattr(app_module, "session_scope", lambda: _Session())
    monkeypatch.setattr(
        app_module.conversations_store, "get_conversation", _get_conversation
    )


def test_owned_conversation_lets_unclaimed_threads_through(monkeypatch):
    """A thread with no row yet is legitimate (the client creates it first)."""
    _patch_ownership(monkeypatch, None)
    me = auth_module.CurrentUser(id=1, email="me@example.com")
    assert _run(app_module._owned_conversation("t-1", me)) is None
    with pytest.raises(auth_module.HTTPException):
        _run(app_module._owned_conversation("t-1", me, required=True))


def test_owned_conversation_blocks_a_legacy_row(monkeypatch):
    """The container for a legacy thread must not be reattachable."""
    _patch_ownership(monkeypatch, _FakeConv(None))
    me = auth_module.CurrentUser(id=1, email="me@example.com")
    with pytest.raises(auth_module.HTTPException) as excinfo:
        _run(app_module._owned_conversation("legacy", me))
    assert excinfo.value.status_code == 404


def test_chat_stream_is_gated_before_any_container_is_created(monkeypatch):
    """/chat/stream must 404 before _get_or_create_session runs.

    Ordering is the whole point: the ownership check sits above the Docker
    call, so an unauthorised id can never spin a sandbox up (nor reattach to
    one).
    """
    _patch_ownership(monkeypatch, _FakeConv(999))

    def _explode(thread_id: str):  # pragma: no cover - must not be reached
        raise AssertionError("container was created before the ownership check")

    monkeypatch.setattr(app_module, "_get_or_create_session", _explode)

    me = auth_module.CurrentUser(id=1, email="me@example.com")
    req = app_module.ChatRequest(message="hi", thread_id="someone-elses-thread")
    with pytest.raises(auth_module.HTTPException) as excinfo:
        _run(app_module.chat_stream(req, object(), me))
    assert excinfo.value.status_code == 404


# ── DB-backed: a throwaway database ─────────────────────────────────────


def _url_for(db_name: str) -> str:
    head, _, _ = _DATABASE_URL.rpartition("/")
    return f"{head}/{db_name}"


def _admin_url() -> str:
    head, _, _ = _DATABASE_URL.rpartition("/")
    return f"{head}/postgres"


async def _provision(name: str):
    """Create a scratch database and return (engine, sessionmaker).

    A separate database, not a schema in the shared one: these tests delete
    rows, and the compose Postgres also holds the developer's real chats.
    """
    from sdlc.db.models import Base

    admin = create_async_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    await admin.dispose()

    engine = create_async_engine(_url_for(name))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # The ORM cannot express a functional index; the migration creates it,
        # so create the same one here and validate its SQL in the process.
        await conn.execute(
            text("CREATE UNIQUE INDEX ux_app_user_email_lower ON app_user (lower(email))")
        )
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _teardown(engine, name: str) -> None:
    await engine.dispose()
    admin = create_async_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :name"
            ),
            {"name": name},
        )
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
    await admin.dispose()


@pytest.fixture(scope="module")
def db():
    """Scratch Postgres + the app's session factory pointed at it."""
    # sys.modules, not "import sdlc.db.engine as ...": sdlc.db re-exports
    # engine as the AsyncEngine instance, which shadows the submodule name.
    import sys

    db_engine = sys.modules["sdlc.db.engine"]

    name = f"harness_auth_test_{uuid.uuid4().hex[:8]}"
    try:
        engine, factory = _run(_provision(name))
    except Exception as exc:  # noqa: BLE001 - any connection failure means skip
        pytest.skip(f"Postgres not reachable at {_DATABASE_URL}: {exc}")

    original = db_engine._SessionFactory
    db_engine._SessionFactory = factory
    try:
        yield factory
    finally:
        db_engine._SessionFactory = original
        _run(_teardown(engine, name))


@pytest.fixture
def client(db):
    import httpx
    from sdlc.api.app import app

    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def _register(client, email: str, password: str = "a long enough passphrase"):
    return await client.post("/auth/register", json={"email": email, "password": password})


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:10]}@example.com"


def test_register_sets_a_cookie_and_me_returns_the_user(client):
    email = _email()

    async def flow():
        assert (await client.get("/auth/me")).status_code == 401

        resp = await _register(client, email)
        assert resp.status_code == 201, resp.text
        assert resp.json()["email"] == email.lower()
        assert "password" not in resp.text and "hash" not in resp.text
        set_cookie = " ".join(resp.headers.get_list("set-cookie"))
        assert "httponly" in set_cookie.lower()
        assert "samesite=lax" in set_cookie.lower()

        me = await client.get("/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == email.lower()

        assert (await client.post("/auth/logout")).status_code == 204
        assert (await client.get("/auth/me")).status_code == 401

    _run(flow())


def test_duplicate_email_is_case_insensitive_and_conflicts(client):
    email = _email()

    async def flow():
        assert (await _register(client, email)).status_code == 201
        dup = await _register(client, email.upper())
        assert dup.status_code == 409
        assert "already exists" in dup.json()["detail"].lower()

    _run(flow())


def test_unknown_email_and_wrong_password_are_indistinguishable(client):
    email = _email()

    async def flow():
        assert (await _register(client, email)).status_code == 201
        await client.post("/auth/logout")
        wrong_password = await client.post(
            "/auth/login", json={"email": email, "password": "definitely-wrong-pass"}
        )
        unknown_email = await client.post(
            "/auth/login",
            json={"email": _email(), "password": "definitely-wrong-pass"},
        )
        assert wrong_password.status_code == unknown_email.status_code == 401
        assert wrong_password.json() == unknown_email.json()

    _run(flow())


def test_login_throttle_returns_429_with_retry_after(client, monkeypatch):
    email = _email()

    async def flow():
        assert (await _register(client, email)).status_code == 201
        await client.post("/auth/logout")
        monkeypatch.setattr(
            auth_module, "_throttle", LoginThrottle(max_attempts=3, window_seconds=60)
        )
        for _ in range(3):
            bad = await client.post(
                "/auth/login", json={"email": email, "password": "wrong-password-here"}
            )
            assert bad.status_code == 401
        blocked = await client.post(
            "/auth/login", json={"email": email, "password": "wrong-password-here"}
        )
        assert blocked.status_code == 429
        assert blocked.headers["retry-after"].isdigit()
        # The right password is also refused while the window is saturated —
        # otherwise the throttle only slows a brute force down instead of
        # stopping the attempt that would have succeeded.
        still_blocked = await client.post(
            "/auth/login",
            json={"email": email, "password": "a long enough passphrase"},
        )
        assert still_blocked.status_code == 429

    _run(flow())


def test_expired_session_is_rejected(client, db):
    email = _email()

    async def flow():
        assert (await _register(client, email)).status_code == 201
        token = client.cookies.get(auth_module.SESSION_COOKIE_NAME)
        assert token

        async with db() as session:
            await session.execute(
                text("UPDATE user_session SET expires_at = :past WHERE token_hash = :h"),
                {
                    "past": datetime.now(timezone.utc) - timedelta(seconds=1),
                    "h": security.hash_token(token),
                },
            )
            await session.commit()

        assert (await client.get("/auth/me")).status_code == 401
        assert client.cookies.get(auth_module.SESSION_COOKIE_NAME) is None

    _run(flow())


def test_conversations_are_isolated_between_users(client):
    """The whole point: B cannot see, read, or write A's conversation."""
    email_a, email_b = _email(), _email()
    thread_id = str(uuid.uuid4())

    async def flow():
        assert (await _register(client, email_a)).status_code == 201
        created = await client.post(
            "/conversations",
            json={"id": thread_id, "title": "A chat", "project_id": "default"},
        )
        assert created.status_code == 200, created.text
        assert (await client.get("/conversations")).json()["conversations"]
        assert (
            await client.post(
                f"/conversations/{thread_id}/messages",
                json={"role": "human", "content": "secret"},
            )
        ).status_code == 200

        # Switch users on the same client; the login replaces the cookie.
        assert (await _register(client, email_b)).status_code == 201

        listing = await client.get("/conversations")
        assert listing.status_code == 200
        assert listing.json()["conversations"] == []

        for path in (
            f"/conversations/{thread_id}/messages",
            f"/conversations/{thread_id}/export",
            f"/conversations/{thread_id}/usage",
            f"/history/{thread_id}",
        ):
            resp = await client.get(path)
            assert resp.status_code == 404, f"{path} leaked A data: {resp.status_code}"

        append = await client.post(
            f"/conversations/{thread_id}/messages",
            json={"role": "human", "content": "injected"},
        )
        assert append.status_code == 404
        assert (await client.delete(f"/conversations/{thread_id}")).status_code == 404
        assert (await client.delete(f"/session/{thread_id}")).status_code == 404

        # And A still owns it.
        relogin = await client.post(
            "/auth/login",
            json={"email": email_a, "password": "a long enough passphrase"},
        )
        assert relogin.status_code == 200
        mine = (await client.get("/conversations")).json()["conversations"]
        assert [c["id"] for c in mine] == [thread_id]

    _run(flow())


def test_legacy_conversations_are_invisible_to_everyone(client, db):
    """A pre-auth row (user_id NULL) is not claimable by the first account."""
    legacy_id = str(uuid.uuid4())

    async def flow():
        async with db() as session:
            await session.execute(
                text(
                    "INSERT INTO conversation (id, title, project_id, user_id) "
                    "VALUES (:id, 'legacy', 'default', NULL)"
                ),
                {"id": legacy_id},
            )
            await session.commit()

        assert (await _register(client, _email())).status_code == 201
        assert (await client.get("/conversations")).json()["conversations"] == []
        for path in (f"/conversations/{legacy_id}/messages", f"/history/{legacy_id}"):
            assert (await client.get(path)).status_code == 404

    _run(flow())


def test_password_change_revokes_other_sessions_only(client):
    email = _email()
    password = "a long enough passphrase"
    new_password = "an even longer passphrase"

    async def flow():
        import httpx
        from sdlc.api.app import app

        transport = httpx.ASGITransport(app=app)
        other = httpx.AsyncClient(transport=transport, base_url="http://testserver")
        try:
            assert (await _register(client, email, password)).status_code == 201
            assert (
                await other.post(
                    "/auth/login", json={"email": email, "password": password}
                )
            ).status_code == 200

            changed = await client.post(
                "/auth/password",
                json={"current_password": password, "new_password": new_password},
            )
            assert changed.status_code == 200, changed.text

            # The caller's own session survives; the other browser does not.
            assert (await client.get("/auth/me")).status_code == 200
            assert (await other.get("/auth/me")).status_code == 401

            # The old password is gone, the new one works.
            assert (
                await other.post(
                    "/auth/login", json={"email": email, "password": password}
                )
            ).status_code == 401
            assert (
                await other.post(
                    "/auth/login", json={"email": email, "password": new_password}
                )
            ).status_code == 200
        finally:
            await other.aclose()

    _run(flow())


def test_protected_endpoints_reject_anonymous_callers(client):
    """/health stays public; everything else needs a session."""

    async def flow():
        assert (await client.get("/health")).status_code == 200
        for path in ("/conversations", "/projects/x/files", "/settings/model", "/skills"):
            assert (await client.get(path)).status_code == 401, path

    _run(flow())
