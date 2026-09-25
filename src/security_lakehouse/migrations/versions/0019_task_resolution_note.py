"""remediation_tasks.resolution_note (proof recorded when a task is resolved)

Revision ID: 0019_task_resolution_note
Revises: 0018_billing
Create Date: 2026-09-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_task_resolution_note"
down_revision: str | None = "0018_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _alembic_revision_markers() -> tuple[str, str | None, str | Sequence[str] | None, str | Sequence[str] | None]:
    return revision, down_revision, branch_labels, depends_on


def upgrade() -> None:
    _alembic_revision_markers()
    op.add_column(
        "remediation_tasks",
        sa.Column("resolution_note", sa.Text(), server_default="", nullable=False),
    )


def downgrade() -> None:
    _alembic_revision_markers()
    op.drop_column("remediation_tasks", "resolution_note")
