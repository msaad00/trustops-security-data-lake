"""FastAPI dependencies for authentication and scope enforcement."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from security_lakehouse.auth.rbac import Identity, scopes_for_role
from security_lakehouse.auth.sessions import SESSION_COOKIE, decode_session_cookie
from security_lakehouse.db import repository

_bearer = HTTPBearer(auto_error=False)

_INSECURE_IDENTITY = Identity(
    user_id="insecure",
    tenant_id="insecure",
    email="insecure@localhost",
    role="admin",
    scopes=scopes_for_role("admin"),
    workspace_id="insecure",
)


def get_session(request: Request) -> Iterator[Session]:
    """Yield a per-request session from the app's session factory."""
    factory = request.app.state.sessionmaker
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_identity(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> Identity:
    """Resolve the authenticated identity, or raise 401."""
    if not getattr(request.app.state, "require_auth", True):
        request.state.identity = _INSECURE_IDENTITY
        return _INSECURE_IDENTITY
    now = datetime.now(UTC)

    # 1. API key (agents/CI): Authorization: Bearer <token>
    if credentials is not None and credentials.credentials:
        key = repository.resolve_api_key(session, credentials.credentials)
        if key is None or not key.is_active(now=now):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or inactive token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not key.user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user is disabled")
        key.last_used_at = now
        session.commit()
        identity = Identity(
            user_id=key.user_id,
            tenant_id=key.tenant_id,
            email=key.user.email,
            role=key.user.role,
            scopes=scopes_for_role(key.user.role),
            workspace_id=key.workspace_id,
            api_key_id=key.id,
        )
        request.state.identity = identity
        return identity

    # 2. Browser session (SSO): httpOnly cookie
    cookie_raw = request.cookies.get(SESSION_COOKIE)
    if cookie_raw:
        session_token = decode_session_cookie(cookie_raw)
        if session_token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired session")
        sess = repository.resolve_user_session(session, session_token)
        if sess is None or not sess.is_active(now=now):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired session")
        if not sess.user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user is disabled")
        identity = Identity(
            user_id=sess.user_id,
            tenant_id=sess.tenant_id,
            email=sess.user.email,
            role=sess.user.role,
            scopes=scopes_for_role(sess.user.role),
            workspace_id=sess.tenant_id,
        )
        request.state.identity = identity
        return identity

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="missing credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_scope(scope: str) -> Callable[..., Identity]:
    """Build a dependency that enforces ``scope`` on top of authentication."""

    def dependency(identity: Identity = Depends(get_identity)) -> Identity:
        if not identity.has_scope(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"requires scope: {scope}",
            )
        return identity

    return dependency
