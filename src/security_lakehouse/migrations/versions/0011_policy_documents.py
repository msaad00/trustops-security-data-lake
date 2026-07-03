"""policy documents table

Revision ID: 0011_policy_documents
Revises: 0010_vendor_assessments
Create Date: 2026-07-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_policy_documents"
down_revision: str | None = "0010_vendor_assessments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _alembic_revision_markers() -> tuple[str, str | None, str | Sequence[str] | None, str | Sequence[str] | None]:
    return revision, down_revision, branch_labels, depends_on


def upgrade() -> None:
    _alembic_revision_markers()
    op.create_table(
        "policy_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("content", sa.Text(), server_default="", nullable=False),
        sa.Column("variables_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("related_control_ids_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("owner", sa.String(length=255), server_default="", nullable=False),
        sa.Column("created_by", sa.String(length=255), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_policy_documents_tenant_id", "policy_documents", ["tenant_id"])
    op.create_index("ix_policy_documents_template_id", "policy_documents", ["template_id"])
    op.create_index("ix_policy_documents_tenant_status", "policy_documents", ["tenant_id", "status"])


def downgrade() -> None:
    _alembic_revision_markers()
    op.drop_index("ix_policy_documents_tenant_status", table_name="policy_documents")
    op.drop_index("ix_policy_documents_template_id", table_name="policy_documents")
    op.drop_index("ix_policy_documents_tenant_id", table_name="policy_documents")
    op.drop_table("policy_documents")
