"""access review campaigns + items

Revision ID: 0009_access_reviews
Revises: 0008_agent_runs
Create Date: 2026-06-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_access_reviews"
down_revision: str | None = "0008_agent_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _alembic_revision_markers() -> tuple[str, str | None, str | Sequence[str] | None, str | Sequence[str] | None]:
    """Expose Alembic revision globals to static analysis without renaming them."""
    return revision, down_revision, branch_labels, depends_on


def upgrade() -> None:
    _alembic_revision_markers()
    op.create_table(
        "access_review_campaigns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("scope", sa.String(length=128), server_default="all", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("control_id", sa.String(length=128), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_review_campaigns_tenant_id", "access_review_campaigns", ["tenant_id"])
    op.create_index("ix_access_review_campaigns_control_id", "access_review_campaigns", ["control_id"])
    op.create_index("ix_access_review_campaigns_tenant_status", "access_review_campaigns", ["tenant_id", "status"])

    op.create_table(
        "access_review_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("subject_id", sa.String(length=255), nullable=False),
        sa.Column("subject_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("source", sa.String(length=64), server_default="", nullable=False),
        sa.Column("access_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("decision", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("reviewer", sa.String(length=255), server_default="", nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["access_review_campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_review_items_tenant_id", "access_review_items", ["tenant_id"])
    op.create_index("ix_access_review_items_campaign_id", "access_review_items", ["campaign_id"])
    op.create_index("ix_access_review_items_campaign_decision", "access_review_items", ["campaign_id", "decision"])


def downgrade() -> None:
    _alembic_revision_markers()
    op.drop_index("ix_access_review_items_campaign_decision", table_name="access_review_items")
    op.drop_index("ix_access_review_items_campaign_id", table_name="access_review_items")
    op.drop_index("ix_access_review_items_tenant_id", table_name="access_review_items")
    op.drop_table("access_review_items")
    op.drop_index("ix_access_review_campaigns_tenant_status", table_name="access_review_campaigns")
    op.drop_index("ix_access_review_campaigns_control_id", table_name="access_review_campaigns")
    op.drop_index("ix_access_review_campaigns_tenant_id", table_name="access_review_campaigns")
    op.drop_table("access_review_campaigns")
