"""grc risk register table

Revision ID: 0007_risks
Revises: 0006_metrics
Create Date: 2026-06-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_risks"
down_revision: str | None = "0006_metrics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _alembic_revision_markers() -> tuple[str, str | None, str | Sequence[str] | None, str | Sequence[str] | None]:
    """Expose Alembic revision globals to static analysis without renaming them."""
    return revision, down_revision, branch_labels, depends_on


def upgrade() -> None:
    _alembic_revision_markers()
    op.create_table(
        "risks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("category", sa.String(length=128), server_default="", nullable=False),
        sa.Column("severity", sa.String(length=16), server_default="medium", nullable=False),
        sa.Column("likelihood", sa.String(length=16), server_default="medium", nullable=False),
        sa.Column("impact", sa.String(length=16), server_default="medium", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("treatment", sa.Text(), server_default="", nullable=False),
        sa.Column("owner", sa.String(length=255), server_default="", nullable=False),
        sa.Column("control_id", sa.String(length=128), nullable=True),
        sa.Column("asset_id", sa.String(length=255), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risks_tenant_id", "risks", ["tenant_id"])
    op.create_index("ix_risks_control_id", "risks", ["control_id"])
    op.create_index("ix_risks_asset_id", "risks", ["asset_id"])
    op.create_index("ix_risks_tenant_status", "risks", ["tenant_id", "status"])


def downgrade() -> None:
    _alembic_revision_markers()
    op.drop_index("ix_risks_tenant_status", table_name="risks")
    op.drop_index("ix_risks_asset_id", table_name="risks")
    op.drop_index("ix_risks_control_id", table_name="risks")
    op.drop_index("ix_risks_tenant_id", table_name="risks")
    op.drop_table("risks")
