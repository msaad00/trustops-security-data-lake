"""POA&M request models for gov-compliance routes."""

from __future__ import annotations

from security_lakehouse.server_routes.schemas.base import StrictModel


class CreatePoamItemRequest(StrictModel):
    requirement_id: str
    control_id: str
    title: str
    weakness: str = ""
    framework_id: str = "cmmc-2-level2"
    owner: str = ""
    milestone: str = ""
    sprs_points: int = 1
    poam_eligible: bool = True
    due_at: str | None = None
    remediation_task_id: str | None = None


class UpdatePoamItemRequest(StrictModel):
    status: str | None = None
    owner: str | None = None
    milestone: str | None = None
    weakness: str | None = None
    due_at: str | None = None
    remediation_task_id: str | None = None
