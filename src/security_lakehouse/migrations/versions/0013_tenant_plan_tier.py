"""tenant plan_tier column (commercial hosted)

Revision ID: 0013_tenant_plan_tier
Revises: 0012_tenant_invites
Create Date: 2026-07-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_tenant_plan_tier"
down_revision: str | None = "0012_tenant_invites"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _alembic_revision_markers() -> tuple[str, str | None, str | Sequence[str] | None, str | Sequence[str] | None]:
    return revision, down_revision, branch_labels, depends_on


def upgrade() -> None:
    _alembic_revision_markers()
    op.add_column(
        "tenants",
        sa.Column("plan_tier", sa.String(length=32), server_default="starter", nullable=False),
    )


def downgrade() -> None:
    _alembic_revision_markers()
    op.drop_column("tenants", "plan_tier")
