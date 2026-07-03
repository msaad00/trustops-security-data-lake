"""Usage limits for commercial hosted tenants."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from security_lakehouse.commercial.email import commercial_hosted_enabled
from security_lakehouse.commercial.pricing import get_tier, tier_limits
from security_lakehouse.db.models import ApiKey, Tenant, TenantInvite, User


def tenant_plan_tier(tenant: Tenant) -> str:
    tier = getattr(tenant, "plan_tier", None) or "starter"
    return str(tier).strip().lower() or "starter"


def tenant_usage(session: Session, *, tenant_id: str) -> dict[str, int]:
    users = session.scalar(select(func.count()).select_from(User).where(User.tenant_id == tenant_id)) or 0
    api_keys = (
        session.scalar(
            select(func.count())
            .select_from(ApiKey)
            .where(ApiKey.tenant_id == tenant_id, ApiKey.revoked_at.is_(None))
        )
        or 0
    )
    invites_pending = (
        session.scalar(
            select(func.count())
            .select_from(TenantInvite)
            .where(TenantInvite.tenant_id == tenant_id, TenantInvite.status == "pending")
        )
        or 0
    )
    return {
        "users": int(users),
        "api_keys": int(api_keys),
        "invites_pending": int(invites_pending),
    }


def usage_summary(session: Session, *, tenant: Tenant) -> dict[str, Any]:
    tier_id = tenant_plan_tier(tenant)
    limits = tier_limits(tier_id)
    usage = tenant_usage(session, tenant_id=tenant.id)
    tier = get_tier(tier_id)
    return {
        "tenant_id": tenant.id,
        "plan_tier": tier_id,
        "plan_name": tier["name"] if tier else tier_id,
        "usage": usage,
        "limits": limits,
        "within_limits": {
            "users": usage["users"] < limits["max_users"],
            "api_keys": usage["api_keys"] < limits["max_api_keys"],
            "invites_pending": usage["invites_pending"] < limits["max_invites_pending"],
        },
    }


class UsageLimitError(ValueError):
    """Raised when a tenant exceeds its plan limits."""


def assert_within_limit(session: Session, *, tenant: Tenant, resource: str, delta: int = 1) -> None:
    if not commercial_hosted_enabled():
        return
    summary = usage_summary(session, tenant=tenant)
    usage = summary["usage"]
    limits = summary["limits"]
    key = {
        "users": "max_users",
        "api_keys": "max_api_keys",
        "invites_pending": "max_invites_pending",
    }.get(resource)
    if key is None:
        raise ValueError(f"unknown usage resource {resource!r}")
    if usage[resource] + delta > limits[key]:
        raise UsageLimitError(
            f"plan {summary['plan_tier']} limit exceeded for {resource}: "
            f"{usage[resource] + delta} > {limits[key]}"
        )


__all__ = [
    "UsageLimitError",
    "assert_within_limit",
    "tenant_plan_tier",
    "tenant_usage",
    "usage_summary",
]
