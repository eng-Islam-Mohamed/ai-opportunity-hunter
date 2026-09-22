"""campaign and service catalog foundation

Revision ID: 20260705_0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260705_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

campaign_status = sa.Enum(
    "DRAFT",
    "QUEUED",
    "DISCOVERING",
    "NORMALIZING",
    "ENRICHING",
    "AUDITING",
    "ANALYZING",
    "SCORING",
    "READY_FOR_REVIEW",
    "EXPORTING",
    "COMPLETED",
    "PARTIALLY_COMPLETED",
    "FAILED",
    "CANCELLED",
    name="campaignstatus",
)


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "service_catalog_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("supported_problem_categories", sa.JSON(), nullable=False),
        sa.Column("ideal_customer_profiles", sa.JSON(), nullable=False),
        sa.Column("minimum_evidence_strength", sa.Numeric(4, 3), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_service_workspace_slug"),
    )
    op.create_index(
        "ix_service_catalog_items_workspace_id", "service_catalog_items", ["workspace_id"]
    )
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", campaign_status, nullable=False),
        sa.Column("worker_backend", sa.String(length=32), nullable=False),
        sa.Column("execution_config", sa.JSON(), nullable=False),
        sa.Column("target", sa.JSON(), nullable=False),
        sa.Column("limits", sa.JSON(), nullable=False),
        sa.Column("qualification", sa.JSON(), nullable=False),
        sa.Column("analysis_preferences", sa.JSON(), nullable=False),
        sa.Column("export_config", sa.JSON(), nullable=False),
        sa.Column("progress", sa.JSON(), nullable=False),
        sa.Column("error_summary", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaigns_status", "campaigns", ["status"])
    op.create_index("ix_campaigns_workspace_id", "campaigns", ["workspace_id"])
    op.create_table(
        "campaign_services",
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("service_catalog_item_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["service_catalog_item_id"], ["service_catalog_items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("campaign_id", "service_catalog_item_id"),
    )


def downgrade() -> None:
    op.drop_table("campaign_services")
    op.drop_index("ix_campaigns_workspace_id", table_name="campaigns")
    op.drop_index("ix_campaigns_status", table_name="campaigns")
    op.drop_table("campaigns")
    op.drop_index("ix_service_catalog_items_workspace_id", table_name="service_catalog_items")
    op.drop_table("service_catalog_items")
    op.drop_table("workspaces")
    campaign_status.drop(op.get_bind(), checkfirst=True)
