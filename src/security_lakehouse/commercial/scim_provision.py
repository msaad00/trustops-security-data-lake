"""Minimal SCIM 2.0 User provisioning for commercial hosted tenants."""

from __future__ import annotations

import os
import secrets
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from security_lakehouse.commercial.limits import assert_within_limit
from security_lakehouse.commercial.scim import scim_enabled
from security_lakehouse.db.models import USER_ROLES, User


def scim_bearer_token() -> str | None:
    return os.environ.get("TRUSTOPS_SCIM_BEARER_TOKEN", "").strip() or None


def verify_scim_bearer(provided: str | None) -> bool:
    expected = scim_bearer_token()
    if not expected:
        return False
    return secrets.compare_digest(provided or "", expected)


def scim_bearer_from_authorization(header_value: str | None) -> str:
    """Extract bearer token from an Authorization header without logging it."""
    if not header_value:
        return ""
    lowered = header_value.lower()
    if not lowered.startswith("bearer "):
        return ""
    return header_value[7:].strip()


def require_scim_bearer(header_value: str | None) -> None:
    """Raise ValueError when SCIM bearer auth fails."""
    if not verify_scim_bearer(scim_bearer_from_authorization(header_value)):
        raise ValueError("invalid SCIM bearer token")


def _scim_user(row: User) -> dict[str, Any]:
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": row.id,
        "userName": row.email,
        "name": {"formatted": row.display_name or row.email},
        "emails": [{"value": row.email, "primary": True}],
        "active": bool(row.is_active),
        "meta": {
            "resourceType": "User",
            "created": row.created_at.isoformat() if row.created_at else None,
        },
        "trustopsRole": row.role,
    }


def resolve_scim_tenant_id(session: Session) -> str:
    """Default SCIM tenant slug from env for single-tenant hosted workspaces."""
    from security_lakehouse.db import repository

    slug = os.environ.get("TRUSTOPS_SCIM_TENANT_SLUG", os.environ.get("TRUSTOPS_OIDC_TENANT_SLUG", "default")).strip()
    tenant = repository.get_tenant_by_slug(session, slug=slug)
    if tenant is None:
        raise ValueError(f"SCIM tenant slug {slug!r} does not exist")
    return tenant.id


def list_scim_users(session: Session, *, tenant_id: str, start_index: int = 1, count: int = 100) -> dict[str, Any]:
    rows = list(
        session.scalars(
            select(User)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at)
            .offset(max(0, start_index - 1))
            .limit(count)
        )
    )
    total = session.scalar(select(func.count()).select_from(User).where(User.tenant_id == tenant_id)) or 0
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": int(total),
        "startIndex": start_index,
        "itemsPerPage": len(rows),
        "Resources": [_scim_user(row) for row in rows],
    }


def create_scim_user(
    session: Session,
    *,
    tenant_id: str,
    email: str,
    role: str = "read_only",
    display_name: str = "",
    active: bool = True,
) -> dict[str, Any]:
    from security_lakehouse.db.models import Tenant

    if not scim_enabled():
        raise ValueError("SCIM is not enabled")
    normalized = email.strip().lower()
    if not normalized or "@" not in normalized:
        raise ValueError("userName/email is required")
    if role not in USER_ROLES:
        raise ValueError(f"invalid role {role!r}")
    existing = session.scalars(select(User).where(User.tenant_id == tenant_id, User.email == normalized)).one_or_none()
    if existing is not None:
        raise ValueError("user already exists")
    tenant = session.get(Tenant, tenant_id)
    if tenant is not None:
        assert_within_limit(session, tenant=tenant, resource="users")
    row = User(
        tenant_id=tenant_id,
        email=normalized,
        display_name=display_name.strip() or normalized.split("@", 1)[0],
        role=role,
        is_active=active,
    )
    session.add(row)
    session.flush()
    return _scim_user(row)


def patch_scim_user(
    session: Session,
    *,
    tenant_id: str,
    user_id: str,
    active: bool | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    row = session.get(User, user_id)
    if row is None or row.tenant_id != tenant_id:
        raise ValueError("user not found")
    if role is not None:
        if role not in USER_ROLES:
            raise ValueError(f"invalid role {role!r}")
        row.role = role
    if active is not None:
        row.is_active = active
    session.flush()
    return _scim_user(row)


def get_scim_user(session: Session, *, tenant_id: str, user_id: str) -> dict[str, Any]:
    row = session.get(User, user_id)
    if row is None or row.tenant_id != tenant_id:
        raise ValueError("user not found")
    return _scim_user(row)


def deactivate_scim_user(session: Session, *, tenant_id: str, user_id: str) -> None:
    """SCIM DELETE deactivates the user (soft offboarding) instead of hard delete."""
    row = session.get(User, user_id)
    if row is None or row.tenant_id != tenant_id:
        raise ValueError("user not found")
    row.is_active = False
    session.flush()


__all__ = [
    "create_scim_user",
    "deactivate_scim_user",
    "get_scim_user",
    "list_scim_users",
    "patch_scim_user",
    "require_scim_bearer",
    "resolve_scim_tenant_id",
    "scim_bearer_from_authorization",
    "scim_bearer_token",
    "verify_scim_bearer",
]
