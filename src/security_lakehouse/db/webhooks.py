"""Data-access + serialization for outbound event webhook subscriptions.

Subscriptions and their delivery log live in the application-state database
(server mode). Every query is tenant-scoped so one workspace can never read or
mutate another's registered endpoints, and a subscription's secret is never
returned by ``list``/``get`` serialization — only ``create`` hands it back, once.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from security_lakehouse.db.base import apply_pagination
from security_lakehouse.db.models import (
    WEBHOOK_DELIVERY_STATUSES,
    WEBHOOK_EVENT_TYPES,
    WebhookDelivery,
    WebhookSubscription,
)


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _validate_event_types(event_types: list[str]) -> list[str]:
    if not event_types:
        raise ValueError("event_types must include at least one event type")
    unknown = sorted(set(event_types) - set(WEBHOOK_EVENT_TYPES))
    if unknown:
        raise ValueError(f"unknown event type(s) {unknown}, must be one of {list(WEBHOOK_EVENT_TYPES)}")
    # De-dup, keep stable order.
    seen: list[str] = []
    for event_type in event_types:
        if event_type not in seen:
            seen.append(event_type)
    return seen


def create_subscription(
    session: Session,
    *,
    tenant_id: str,
    url: str,
    secret: str,
    event_types: list[str],
    description: str = "",
    enabled: bool = True,
    created_by: str = "",
) -> WebhookSubscription:
    if not url.strip():
        raise ValueError("webhook requires a url")
    if not secret.strip():
        raise ValueError("webhook requires a secret")
    validated_types = _validate_event_types(event_types)
    subscription = WebhookSubscription(
        tenant_id=tenant_id,
        url=url.strip(),
        secret=secret,
        description=description,
        event_types_json=json.dumps(validated_types),
        enabled=enabled,
        created_by=created_by,
    )
    session.add(subscription)
    session.flush()
    return subscription


def get_subscription(session: Session, *, tenant_id: str, subscription_id: str) -> WebhookSubscription | None:
    subscription = session.get(WebhookSubscription, subscription_id)
    return subscription if subscription is not None and subscription.tenant_id == tenant_id else None


def list_subscriptions(
    session: Session,
    *,
    tenant_id: str,
    enabled: bool | None = None,
    event_type: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[WebhookSubscription]:
    stmt = select(WebhookSubscription).where(WebhookSubscription.tenant_id == tenant_id)
    if enabled is not None:
        stmt = stmt.where(WebhookSubscription.enabled == enabled)
    stmt = apply_pagination(stmt.order_by(WebhookSubscription.created_at.desc()), limit=limit, offset=offset)
    rows = list(session.scalars(stmt))
    if event_type:
        rows = [row for row in rows if event_type in json.loads(row.event_types_json or "[]")]
    return rows


def list_subscriptions_for_event(session: Session, *, tenant_id: str, event_type: str) -> list[WebhookSubscription]:
    """Enabled subscriptions for ``tenant_id`` subscribed to ``event_type`` — the delivery fan-out list."""
    stmt = select(WebhookSubscription).where(
        WebhookSubscription.tenant_id == tenant_id,
        WebhookSubscription.enabled.is_(True),
    )
    rows = list(session.scalars(stmt))
    return [row for row in rows if event_type in json.loads(row.event_types_json or "[]")]


def update_subscription(
    session: Session,
    *,
    tenant_id: str,
    subscription_id: str,
    changes: dict[str, Any],
    now: datetime | None = None,
) -> WebhookSubscription | None:
    subscription = get_subscription(session, tenant_id=tenant_id, subscription_id=subscription_id)
    if subscription is None:
        return None
    if "url" in changes and changes["url"] is not None:
        url = str(changes["url"]).strip()
        if not url:
            raise ValueError("webhook requires a url")
        subscription.url = url
    if "secret" in changes and changes["secret"] is not None:
        secret = str(changes["secret"])
        if not secret.strip():
            raise ValueError("webhook requires a secret")
        subscription.secret = secret
    if "event_types" in changes and changes["event_types"] is not None:
        subscription.event_types_json = json.dumps(_validate_event_types(list(changes["event_types"])))
    if "description" in changes and changes["description"] is not None:
        subscription.description = str(changes["description"])
    if "enabled" in changes and changes["enabled"] is not None:
        subscription.enabled = bool(changes["enabled"])
    subscription.updated_at = _now(now)
    session.flush()
    return subscription


def delete_subscription(session: Session, *, tenant_id: str, subscription_id: str) -> bool:
    subscription = get_subscription(session, tenant_id=tenant_id, subscription_id=subscription_id)
    if subscription is None:
        return False
    session.delete(subscription)
    session.flush()
    return True


def record_delivery_result(
    session: Session,
    *,
    tenant_id: str,
    subscription_id: str,
    event_type: str,
    event_id: str,
    ok: bool,
    attempts: int,
    response_status: int | None,
    error: str = "",
    now: datetime | None = None,
) -> WebhookDelivery:
    moment = _now(now)
    status = "success" if ok else "failed"
    if status not in WEBHOOK_DELIVERY_STATUSES:  # pragma: no cover - defensive, status is derived above
        raise ValueError(f"status must be one of {list(WEBHOOK_DELIVERY_STATUSES)}, got {status!r}")
    delivery = WebhookDelivery(
        tenant_id=tenant_id,
        subscription_id=subscription_id,
        event_type=event_type,
        event_id=event_id,
        status=status,
        attempts=attempts,
        response_status=response_status,
        error=error,
        created_at=moment,
    )
    session.add(delivery)
    subscription = get_subscription(session, tenant_id=tenant_id, subscription_id=subscription_id)
    if subscription is not None:
        subscription.last_delivery_at = moment
        subscription.last_delivery_status = status
    session.flush()
    return delivery


def list_deliveries(
    session: Session,
    *,
    tenant_id: str,
    subscription_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[WebhookDelivery]:
    stmt = select(WebhookDelivery).where(WebhookDelivery.tenant_id == tenant_id)
    if subscription_id:
        stmt = stmt.where(WebhookDelivery.subscription_id == subscription_id)
    stmt = apply_pagination(stmt.order_by(WebhookDelivery.created_at.desc()), limit=limit, offset=offset)
    return list(session.scalars(stmt))


def subscription_to_dict(subscription: WebhookSubscription, *, include_secret: bool = False) -> dict[str, Any]:
    """Serialize a subscription. ``include_secret`` is only ever true right after creation."""
    data: dict[str, Any] = {
        "id": subscription.id,
        "url": subscription.url,
        "description": subscription.description,
        "event_types": json.loads(subscription.event_types_json or "[]"),
        "enabled": subscription.enabled,
        "created_at": _iso(subscription.created_at),
        "updated_at": _iso(subscription.updated_at),
        "last_delivery_at": _iso(subscription.last_delivery_at),
        "last_delivery_status": subscription.last_delivery_status,
    }
    if include_secret:
        data["secret"] = subscription.secret
    return data


def delivery_to_dict(delivery: WebhookDelivery) -> dict[str, Any]:
    return {
        "id": delivery.id,
        "subscription_id": delivery.subscription_id,
        "event_type": delivery.event_type,
        "event_id": delivery.event_id,
        "status": delivery.status,
        "attempts": delivery.attempts,
        "response_status": delivery.response_status,
        "error": delivery.error,
        "created_at": _iso(delivery.created_at),
    }


__all__ = [
    "WEBHOOK_EVENT_TYPES",
    "create_subscription",
    "delete_subscription",
    "delivery_to_dict",
    "get_subscription",
    "list_deliveries",
    "list_subscriptions",
    "list_subscriptions_for_event",
    "record_delivery_result",
    "subscription_to_dict",
    "update_subscription",
]
