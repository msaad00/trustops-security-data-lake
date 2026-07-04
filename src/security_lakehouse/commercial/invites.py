"""Tenant invite lifecycle for commercial hosted workspaces."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from security_lakehouse.commercial.email import (
    EmailDelivery,
    EmailMessage,
    commercial_hosted_enabled,
    email_delivery_from_env,
)
from security_lakehouse.commercial.limits import assert_within_limit
from security_lakehouse.db.models import Tenant, TenantInvite, User

INVITE_TTL_HOURS = 168  # 7 days


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _public_base_url() -> str:
    import os

    return os.environ.get("TRUSTOPS_PUBLIC_URL", "http://127.0.0.1:8787").rstrip("/")


def create_invite(
    session: Session,
    *,
    tenant_id: str,
    email: str,
    role: str,
    invited_by: str,
    delivery: EmailDelivery | None = None,
) -> tuple[TenantInvite, str]:
    """Create an invite and optionally send email. Returns (row, plaintext_token)."""
    if not commercial_hosted_enabled():
        raise ValueError("commercial hosted invites require TRUSTOPS_COMMERCIAL_HOSTED=1")
    normalized = email.strip().lower()
    if not normalized:
        raise ValueError("email is required")
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("tenant not found")
    assert_within_limit(session, tenant=tenant, resource="invites_pending")
    token = secrets.token_urlsafe(32)
    moment = datetime.now(UTC)
    row = TenantInvite(
        tenant_id=tenant_id,
        email=normalized,
        role=role,
        token_hash=_hash_token(token),
        status="pending",
        invited_by=invited_by,
        expires_at=moment + timedelta(hours=INVITE_TTL_HOURS),
    )
    session.add(row)
    session.flush()
    accept_url = f"{_public_base_url()}/console/login/?invite={token}"
    sender = delivery or email_delivery_from_env()
    sender.send(
        EmailMessage(
            to=normalized,
            subject="You're invited to TrustOps",
            body_text=(
                f"You have been invited to TrustOps as {role}.\n\n"
                f"Accept: {accept_url}\n\n"
                f"This link expires in {INVITE_TTL_HOURS} hours."
            ),
        )
    )
    return row, token


def list_invites(session: Session, *, tenant_id: str, limit: int = 100) -> list[TenantInvite]:
    stmt = (
        select(TenantInvite)
        .where(TenantInvite.tenant_id == tenant_id)
        .order_by(TenantInvite.created_at.desc())
        .limit(max(1, min(limit, 500)))
    )
    return list(session.scalars(stmt))


def accept_invite(
    session: Session,
    *,
    token: str,
    display_name: str = "",
) -> dict[str, Any]:
    """Accept a pending invite; returns user summary."""
    if not commercial_hosted_enabled():
        raise ValueError("commercial hosted invites require TRUSTOPS_COMMERCIAL_HOSTED=1")
    digest = _hash_token(token.strip())
    row = session.scalars(select(TenantInvite).where(TenantInvite.token_hash == digest)).one_or_none()
    if row is None:
        raise ValueError("invite not found")
    if row.status != "pending":
        raise ValueError(f"invite is {row.status}")
    tenant = session.get(Tenant, row.tenant_id)
    if tenant is None:
        raise ValueError("tenant not found")
    assert_within_limit(session, tenant=tenant, resource="users")
    now = datetime.now(UTC)
    expires = row.expires_at.replace(tzinfo=UTC) if row.expires_at.tzinfo is None else row.expires_at.astimezone(UTC)
    if expires < now:
        row.status = "expired"
        session.flush()
        raise ValueError("invite expired")
    user = User(
        tenant_id=row.tenant_id,
        email=row.email,
        display_name=display_name or row.email.split("@", 1)[0],
        role=row.role,
        is_active=True,
    )
    session.add(user)
    row.status = "accepted"
    row.accepted_at = now
    row.accepted_user_id = user.id
    session.flush()
    return {"user_id": user.id, "email": user.email, "role": user.role, "tenant_id": user.tenant_id}


def invite_to_dict(row: TenantInvite) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "email": row.email,
        "role": row.role,
        "status": row.status,
        "invited_by": row.invited_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "accepted_at": row.accepted_at.isoformat() if row.accepted_at else None,
    }


__all__ = [
    "accept_invite",
    "create_invite",
    "invite_to_dict",
    "list_invites",
]
