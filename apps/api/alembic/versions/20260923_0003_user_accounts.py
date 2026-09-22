"""user accounts and daily campaign quotas

Revision ID: 20260923_0003
Revises: 20260705_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260923_0003"
down_revision: str | None = "20260705_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.add_column("workspaces", sa.Column("owner_user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_workspaces_owner_user", "workspaces", "users", ["owner_user_id"], ["id"], ondelete="CASCADE")
    op.create_unique_constraint("uq_workspaces_owner_user", "workspaces", ["owner_user_id"])
    op.create_table(
        "daily_campaign_usage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("campaign_runs", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_daily_campaign_usage"),
    )
    op.create_index("ix_daily_campaign_usage_user_id", "daily_campaign_usage", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_daily_campaign_usage_user_id", table_name="daily_campaign_usage")
    op.drop_table("daily_campaign_usage")
    op.drop_constraint("uq_workspaces_owner_user", "workspaces", type_="unique")
    op.drop_constraint("fk_workspaces_owner_user", "workspaces", type_="foreignkey")
    op.drop_column("workspaces", "owner_user_id")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
