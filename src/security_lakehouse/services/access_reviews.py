"""Shared access-review service functions (campaigns + items).

Transport-agnostic wrappers over the ``db.access_reviews`` repository plus
serialization, mirroring :mod:`security_lakehouse.services.grc`. Write functions
own their commit so any caller — FastAPI routes, the MCP server, the SDK, or the
CLI — gets durable DB-backed writes. Repository ``ValueError`` is surfaced as
:class:`ValidationError`; missing rows as :class:`NotFound`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from security_lakehouse.db import access_reviews as ar
from security_lakehouse.services import NotFound, ValidationError


def list_campaigns(
    session: Session,
    tenant_id: str,
    *,
    status: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict[str, Any]]:
    rows = ar.list_campaigns(session, tenant_id=tenant_id, status=status, limit=limit, offset=offset)
    return [ar.campaign_to_dict(row) for row in rows]


def create_campaign(
    session: Session,
    tenant_id: str,
    *,
    name: str,
    description: str = "",
    scope: str = "all",
    control_id: str | None = None,
    due_at: datetime | None = None,
    created_by: str = "",
) -> dict[str, Any]:
    try:
        campaign = ar.create_campaign(
            session,
            tenant_id=tenant_id,
            name=name,
            description=description,
            scope=scope,
            control_id=control_id,
            due_at=due_at,
            created_by=created_by,
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    session.commit()
    return ar.campaign_to_dict(campaign)


def get_campaign(session: Session, tenant_id: str, campaign_id: str) -> dict[str, Any]:
    campaign = ar.get_campaign(session, tenant_id=tenant_id, campaign_id=campaign_id)
    if campaign is None:
        raise NotFound("access review campaign not found")
    data = ar.campaign_to_dict(campaign)
    data["progress"] = ar.campaign_progress(session, tenant_id=tenant_id, campaign_id=campaign_id)
    return data


def set_campaign_status(session: Session, tenant_id: str, campaign_id: str, *, status: str) -> dict[str, Any]:
    try:
        campaign = ar.set_campaign_status(session, tenant_id=tenant_id, campaign_id=campaign_id, status=status)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    if campaign is None:
        raise NotFound("access review campaign not found")
    session.commit()
    return ar.campaign_to_dict(campaign)


def list_items(
    session: Session,
    tenant_id: str,
    campaign_id: str,
    *,
    decision: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict[str, Any]]:
    if ar.get_campaign(session, tenant_id=tenant_id, campaign_id=campaign_id) is None:
        raise NotFound("access review campaign not found")
    rows = ar.list_items(
        session, tenant_id=tenant_id, campaign_id=campaign_id, decision=decision, limit=limit, offset=offset
    )
    return [ar.item_to_dict(row) for row in rows]


def add_item(
    session: Session,
    tenant_id: str,
    campaign_id: str,
    *,
    subject_id: str,
    subject_name: str = "",
    source: str = "",
    access_summary: str = "",
) -> dict[str, Any]:
    try:
        item = ar.add_item(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            subject_id=subject_id,
            subject_name=subject_name,
            source=source,
            access_summary=access_summary,
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    session.commit()
    return ar.item_to_dict(item)


def record_decision(
    session: Session,
    tenant_id: str,
    item_id: str,
    *,
    decision: str,
    reviewer: str = "",
    note: str = "",
) -> dict[str, Any]:
    try:
        item = ar.record_decision(
            session, tenant_id=tenant_id, item_id=item_id, decision=decision, reviewer=reviewer, note=note
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    if item is None:
        raise NotFound("access review item not found")
    session.commit()
    return ar.item_to_dict(item)


__all__ = [
    "add_item",
    "create_campaign",
    "get_campaign",
    "list_campaigns",
    "list_items",
    "record_decision",
    "set_campaign_status",
]
