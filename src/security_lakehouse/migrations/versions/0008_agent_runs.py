"""agent harness run records

Revision ID: 0008_agent_runs
Revises: 0007_risks
Create Date: 2026-06-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_agent_runs"
down_revision: str | None = "0007_risks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _alembic_revision_markers() -> tuple[str, str | None, str | Sequence[str] | None, str | Sequence[str] | None]:
    """Expose Alembic revision globals to static analysis without renaming them."""
    return revision, down_revision, branch_labels, depends_on


def upgrade() -> None:
    _alembic_revision_markers()
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("harness", sa.String(length=64), nullable=False),
        sa.Column("objective", sa.Text(), server_default="", nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), server_default="rules_only", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="completed", nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("provider_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("budget_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("evaluation_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("decisions_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("state_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("errors_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("created_by", sa.String(length=255), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_agent_runs_tenant_idempotency_key"),
    )
    op.create_index("ix_agent_runs_tenant_id", "agent_runs", ["tenant_id"])
    op.create_index("ix_agent_runs_tenant_harness_created", "agent_runs", ["tenant_id", "harness", "created_at"])
    op.create_index("ix_agent_runs_tenant_status", "agent_runs", ["tenant_id", "status"])


def downgrade() -> None:
    _alembic_revision_markers()
    op.drop_index("ix_agent_runs_tenant_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_tenant_harness_created", table_name="agent_runs")
    op.drop_index("ix_agent_runs_tenant_id", table_name="agent_runs")
    op.drop_table("agent_runs")
