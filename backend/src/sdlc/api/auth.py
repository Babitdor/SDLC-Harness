"""Accounts and cookie sessions: ``/auth/*`` plus the ``require_user`` gate.

Why a cookie and not a bearer token: the frontend is a same-site browser app
(Next on :3000, FastAPI on :8000 — same site, ports do not change it), and it
streams SSE through ``fetch`` rather than ``EventSource``. An ``HttpOnly``
cookie therefore needs no token handling in JS and cannot be read by an XSS
payload.

Every protected route gets this dependency, either explicitly (where the
handler needs the user) or through the router-level dependency in
``api/app.py``. ``GET /health`` and the auth endpoints themselves are the only
public surface.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status

from sdlc.core.config import (
    LOGIN_MAX_ATTEMPTS,
    LOGIN_WINDOW_MINUTES,
    MIN_PASSWORD_LENGTH,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE,
    SESSION_TTL_DAYS,
)
from sdlc.core.security import (
    LoginThrottle,
    TooManyAttempts,
    burn_password_time,
    hash_token,
    verify_password,
)
from sdlc.db import session_scope
from sdlc.models.schemas import (
    AuthUser,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
)
from sdlc.services import users as user_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Deliberately loose. Anything stricter starts rejecting addresses that are
# legal and deliverable; the real check is that the account is reachable, and
# there is no mailer here to prove it either way.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

#: One generic message for both unknown email and wrong password, so the
#: response body cannot be used to enumerate accounts.
_BAD_CREDENTIALS = "Invalid email or password"

# Per-process throttle. Keyed by (email, client ip) so neither a single
# address nor a single source can grind the password space.
_throttle = LoginThrottle(
    max_attempts=LOGIN_MAX_ATTEMPTS,
    window_seconds=LOGIN_WINDOW_MINUTES * 60,
)


@dataclass(frozen=True)
class CurrentUser:
    """The authenticated caller, as handlers need it.

    A plain value rather than the ORM row: the session that loaded it is
    closed by the time a handler runs, so handing out a detached ORM object
    invites a DetachedInstanceError on the one attribute nobody expects to be
    lazy.
    """

    id: int
    email: str
    display_name: str = ""


# ── Cookie plumbing ─────────────────────────────────────────────────────


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,  # type: ignore[arg-type]
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,  # type: ignore[arg-type]
        path="/",
    )


def _client_ip(request: Request) -> str:
    # No X-Forwarded-For handling: trusting a client-supplied header would let
    # an attacker pick their own throttle key. Behind a proxy, every request
    # shares one key — still bounded, just coarser.
    return request.client.host if request.client else ""


# ── The gate ────────────────────────────────────────────────────────────


async def require_user(
    request: Request,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> CurrentUser:
    """Resolve the session cookie to a user, or 401.

    Every protected endpoint depends on this. It is also the single override
    point for tests (``app.dependency_overrides[require_user]``).
    """
    if not session_token:
        raise _unauthorized()
    async with session_scope() as db:
        user = await user_store.resolve_session(db, session_token)
    if user is None:
        raise _unauthorized()
    return CurrentUser(id=user.id, email=user.email, display_name=user.display_name or "")


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Cookie"},
    )


def _auth_user(user: CurrentUser) -> AuthUser:
    return AuthUser(id=user.id, email=user.email, display_name=user.display_name)


def _validate_registration(body: RegisterRequest) -> str:
    email = body.email.strip()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if len(body.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
        )
    return email


# ── Endpoints ───────────────────────────────────────────────────────────


@router.post("/register", response_model=AuthUser, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request, response: Response) -> AuthUser:
    """Create an account and sign it in. Open signup, by design."""
    email = _validate_registration(body)
    async with session_scope() as db:
        try:
            user = await user_store.create_user(
                db, email=email, password=body.password, display_name=body.display_name
            )
        except user_store.EmailTaken:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with that email already exists",
            ) from None
        token = await user_store.create_session(
            db,
            user=user,
            ttl_days=SESSION_TTL_DAYS,
            user_agent=request.headers.get("user-agent", ""),
            ip=_client_ip(request),
        )
        payload = AuthUser(id=user.id, email=user.email, display_name=user.display_name or "")
    _set_session_cookie(response, token)
    logger.info("Registered account %s", email)
    return payload


@router.post("/login", response_model=AuthUser)
async def login(body: LoginRequest, request: Request, response: Response) -> AuthUser:
    email = body.email.strip().lower()
    key = f"{email}|{_client_ip(request)}"
    try:
        _throttle.check(key)
    except TooManyAttempts as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from None

    async with session_scope() as db:
        user = await user_store.get_user_by_email(db, email)
        if user is None:
            # Same work as a real verification, so the timing of a 401 does
            # not tell the caller whether the address has an account.
            burn_password_time(body.password)
        elif not verify_password(body.password, user.password_hash or ""):
            user = None
        if user is None or not user.is_active:
            _throttle.fail(key)
            logger.info("Failed login for %s", email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=_BAD_CREDENTIALS
            )
        _throttle.reset(key)
        token = await user_store.create_session(
            db,
            user=user,
            ttl_days=SESSION_TTL_DAYS,
            user_agent=request.headers.get("user-agent", ""),
            ip=_client_ip(request),
        )
        # Opportunistic sweep; login is the natural moment to pay for it.
        await user_store.delete_expired_sessions(db)
        payload = AuthUser(id=user.id, email=user.email, display_name=user.display_name or "")
    _set_session_cookie(response, token)
    return payload


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request) -> Response:
    """Revoke the presented session and clear the cookie.

    Public on purpose: signing out must work with an already-invalid cookie,
    and the only thing an unauthenticated caller can do here is fail to find
    a session to delete.
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        async with session_scope() as db:
            await user_store.revoke_session(db, token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookie(response)
    return response


@router.get("/me", response_model=AuthUser)
async def me(user: CurrentUser = Depends(require_user)) -> AuthUser:
    """Who am I — the frontend's session probe on every page load."""
    return _auth_user(user)


@router.post("/password", response_model=AuthUser)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user: CurrentUser = Depends(require_user),
) -> AuthUser:
    """Change the password and sign out every other browser.

    Re-authenticating with the current password is what stops a stolen cookie
    from becoming a permanent account takeover.
    """
    if len(body.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
        )
    current_token = request.cookies.get(SESSION_COOKIE_NAME) or ""
    async with session_scope() as db:
        row = await user_store.get_user(db, user.id)
        if row is None:
            raise _unauthorized()
        if not verify_password(body.current_password, row.password_hash or ""):
            raise HTTPException(status_code=403, detail="Current password is incorrect")
        await user_store.set_password(db, row, body.new_password)
        revoked = await user_store.revoke_user_sessions(
            db, row.id, except_token_hash=hash_token(current_token) if current_token else None
        )
        email = row.email
    logger.info("Password changed for %s; revoked %d other session(s)", email, revoked)
    return _auth_user(user)
