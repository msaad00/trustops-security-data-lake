"""vendor assessments table

Revision ID: 0010_vendor_assessments
Revises: 0009_access_reviews
Create Date: 2026-07-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_vendor_assessments"
down_revision: str | None = "0009_access_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _alembic_revision_markers() -> tuple[str, str | None, str | Sequence[str] | None, str | Sequence[str] | None]:
    return revision, down_revision, branch_labels, depends_on


def upgrade() -> None:
    _alembic_revision_markers()
    op.create_table(
        "vendor_assessments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("vendor_name", sa.String(length=255), nullable=False),
        sa.Column("template_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("control_id", sa.String(length=128), nullable=True),
        sa.Column("owner", sa.String(length=255), server_default="", nullable=False),
        sa.Column("responses_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vendor_assessments_tenant_id", "vendor_assessments", ["tenant_id"])
    op.create_index("ix_vendor_assessments_template_id", "vendor_assessments", ["template_id"])
    op.create_index("ix_vendor_assessments_control_id", "vendor_assessments", ["control_id"])
    op.create_index("ix_vendor_assessments_tenant_status", "vendor_assessments", ["tenant_id", "status"])


def downgrade() -> None:
    _alembic_revision_markers()
    op.drop_index("ix_vendor_assessments_tenant_status", table_name="vendor_assessments")
    op.drop_index("ix_vendor_assessments_control_id", table_name="vendor_assessments")
    op.drop_index("ix_vendor_assessments_template_id", table_name="vendor_assessments")
    op.drop_index("ix_vendor_assessments_tenant_id", table_name="vendor_assessments")
    op.drop_table("vendor_assessments")
