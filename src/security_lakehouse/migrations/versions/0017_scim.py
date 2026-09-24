"""scim_tokens, scim_groups, scim_group_members; SCIM columns on users

Revision ID: 0017_scim
Revises: 0016_webhooks
Create Date: 2026-09-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_scim"
down_revision: str | None = "0016_webhooks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _alembic_revision_markers() -> tuple[str, str | None, str | Sequence[str] | None, str | Sequence[str] | None]:
    return revision, down_revision, branch_labels, depends_on


def upgrade() -> None:
    _alembic_revision_markers()
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("scim_external_id", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("scim_deleted_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "scim_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.String(length=255), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scim_tokens_tenant_id", "scim_tokens", ["tenant_id"])
    op.create_index("ix_scim_tokens_token_hash", "scim_tokens", ["token_hash"], unique=True)

    op.create_table(
        "scim_groups",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "display_name", name="uq_scim_groups_tenant_name"),
    )
    op.create_index("ix_scim_groups_tenant_id", "scim_groups", ["tenant_id"])

    op.create_table(
        "scim_group_members",
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["scim_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("scim_group_members")
    op.drop_index("ix_scim_groups_tenant_id", table_name="scim_groups")
    op.drop_table("scim_groups")
    op.drop_index("ix_scim_tokens_token_hash", table_name="scim_tokens")
    op.drop_index("ix_scim_tokens_tenant_id", table_name="scim_tokens")
    op.drop_table("scim_tokens")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("scim_deleted_at")
        batch.drop_column("scim_external_id")
