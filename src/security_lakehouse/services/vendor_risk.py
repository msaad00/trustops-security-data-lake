"""Vendor-risk questionnaire service (templates + tenant assessments)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from security_lakehouse.db import vendor_assessments as va
from security_lakehouse.services import NotFound, ValidationError
from security_lakehouse.vendor_questionnaires import (
    get_vendor_questionnaire_template,
    list_vendor_questionnaire_templates,
    score_vendor_responses,
)


def list_templates() -> list[dict[str, Any]]:
    return [
        {
            "template_id": row["template_id"],
            "name": row.get("name"),
            "description": row.get("description"),
            "control_ids": row.get("control_ids") or [],
            "question_count": sum(len(section.get("questions") or []) for section in row.get("sections") or []),
        }
        for row in list_vendor_questionnaire_templates()
    ]


def get_template(template_id: str) -> dict[str, Any]:
    template = get_vendor_questionnaire_template(template_id)
    if template is None:
        raise NotFound("vendor questionnaire template not found")
    return template


def list_assessments(
    session: Session,
    tenant_id: str,
    *,
    status: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict[str, Any]]:
    rows = va.list_assessments(session, tenant_id=tenant_id, status=status, limit=limit, offset=offset)
    return [va.assessment_to_dict(row) for row in rows]


def create_assessment(
    session: Session,
    tenant_id: str,
    *,
    vendor_name: str,
    template_id: str,
    owner: str = "",
    control_id: str | None = None,
    due_at: datetime | None = None,
    created_by: str = "",
) -> dict[str, Any]:
    if get_vendor_questionnaire_template(template_id) is None:
        raise ValidationError(f"unknown vendor questionnaire template: {template_id}")
    try:
        row = va.create_assessment(
            session,
            tenant_id=tenant_id,
            vendor_name=vendor_name,
            template_id=template_id,
            owner=owner,
            control_id=control_id,
            due_at=due_at,
            created_by=created_by,
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    session.commit()
    return va.assessment_to_dict(row)


def get_assessment(session: Session, tenant_id: str, assessment_id: str) -> dict[str, Any]:
    row = va.get_assessment(session, tenant_id=tenant_id, assessment_id=assessment_id)
    if row is None:
        raise NotFound("vendor assessment not found")
    template = get_vendor_questionnaire_template(row.template_id)
    return va.assessment_to_dict(row, template=template)


def update_assessment(
    session: Session,
    tenant_id: str,
    assessment_id: str,
    *,
    changes: dict[str, Any],
) -> dict[str, Any]:
    row = va.get_assessment(session, tenant_id=tenant_id, assessment_id=assessment_id)
    if row is None:
        raise NotFound("vendor assessment not found")
    try:
        updated = va.update_assessment(session, tenant_id=tenant_id, assessment_id=assessment_id, changes=changes)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    if updated is None:
        raise NotFound("vendor assessment not found")
    session.commit()
    template = get_vendor_questionnaire_template(updated.template_id)
    return va.assessment_to_dict(updated, template=template)


def submit_assessment(session: Session, tenant_id: str, assessment_id: str) -> dict[str, Any]:
    row = va.get_assessment(session, tenant_id=tenant_id, assessment_id=assessment_id)
    if row is None:
        raise NotFound("vendor assessment not found")
    template = get_vendor_questionnaire_template(row.template_id)
    if template is None:
        raise ValidationError("assessment template is missing from catalog")
    responses = va.assessment_to_dict(row)["responses"]
    try:
        scored = score_vendor_responses(template, responses)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    updated = va.update_assessment(
        session,
        tenant_id=tenant_id,
        assessment_id=assessment_id,
        changes={
            "status": "completed",
            "score": scored["score"],
            "risk_level": scored["risk_level"],
        },
        now=datetime.now(UTC),
    )
    session.commit()
    return va.assessment_to_dict(updated or row, template=template)
