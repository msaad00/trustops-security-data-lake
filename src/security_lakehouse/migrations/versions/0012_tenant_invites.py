"""tenant invites table (commercial hosted)

Revision ID: 0012_tenant_invites
Revises: 0011_policy_documents
Create Date: 2026-07-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_tenant_invites"
down_revision: str | None = "0011_policy_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _alembic_revision_markers() -> tuple[str, str | None, str | Sequence[str] | None, str | Sequence[str] | None]:
    return revision, down_revision, branch_labels, depends_on


def upgrade() -> None:
    _alembic_revision_markers()
    op.create_table(
        "tenant_invites",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=32), server_default="contributor", nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("invited_by", sa.String(length=320), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_user_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "email", "status", name="uq_tenant_invites_pending_email"),
    )
    op.create_index("ix_tenant_invites_tenant_id", "tenant_invites", ["tenant_id"])
    op.create_index("ix_tenant_invites_token_hash", "tenant_invites", ["token_hash"])


def downgrade() -> None:
    _alembic_revision_markers()
    op.drop_index("ix_tenant_invites_token_hash", table_name="tenant_invites")
    op.drop_index("ix_tenant_invites_tenant_id", table_name="tenant_invites")
    op.drop_table("tenant_invites")
