"""opportunity pipeline entities

Revision ID: 20260705_0002
Revises: 20260705_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260705_0002"
down_revision: str | None = "20260705_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

pipeline_status = sa.Enum(
    "DISCOVERED",
    "DUPLICATE",
    "FILTERED_OUT",
    "QUALIFIED_FOR_ENRICHMENT",
    "ENRICHING",
    "ENRICHMENT_FAILED",
    "QUALIFIED_FOR_AUDIT",
    "AUDITING",
    "AUDIT_FAILED",
    "QUALIFIED_FOR_ANALYSIS",
    "ANALYZING",
    "ANALYSIS_FAILED",
    "SCORED",
    "READY",
    "EXPORTED",
    name="pipelinestatus",
)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("canonical_name", sa.String(300), nullable=False),
        sa.Column("normalized_name", sa.String(300), nullable=False),
        sa.Column("primary_domain", sa.String(255), nullable=True),
        sa.Column("company_type", sa.String(100), nullable=True),
        *timestamps(),
    )
    op.create_index("ix_companies_normalized_name", "companies", ["normalized_name"])
    op.create_index("ix_companies_primary_domain", "companies", ["primary_domain"])
    op.create_table(
        "company_locations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("formatted_address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(150), nullable=True),
        sa.Column("region", sa.String(150), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("source_kind", sa.String(80), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_company_locations_company_id", "company_locations", ["company_id"])
    op.create_table(
        "provider_entities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("provider_entity_id", sa.String(300), nullable=False),
        sa.Column("retention_class", sa.String(80), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("provider_metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("provider", "provider_entity_id", name="uq_provider_entity"),
    )
    op.create_index("ix_provider_entities_company_id", "provider_entities", ["company_id"])
    op.create_table(
        "campaign_companies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pipeline_status", pipeline_status, nullable=False),
        sa.Column("qualification_status", sa.String(80), nullable=False),
        sa.Column("qualification_reason", sa.JSON(), nullable=False),
        sa.Column("priority_order", sa.Integer(), nullable=True),
        *timestamps(),
        sa.UniqueConstraint("campaign_id", "company_id", name="uq_campaign_company"),
    )
    op.create_index("ix_campaign_companies_campaign_id", "campaign_companies", ["campaign_id"])
    op.create_index("ix_campaign_companies_company_id", "campaign_companies", ["company_id"])
    op.create_index(
        "ix_campaign_companies_pipeline_status", "campaign_companies", ["pipeline_status"]
    )
    op.create_table(
        "contact_points",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("verification_status", sa.String(40), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_contact_points_company_id", "contact_points", ["company_id"])
    op.create_table(
        "digital_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("asset_metadata", sa.JSON(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
    )
    op.create_index("ix_digital_assets_company_id", "digital_assets", ["company_id"])
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(80), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.String(80), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_title", sa.Text(), nullable=True),
        sa.Column("observation_data", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("retention_class", sa.String(80), nullable=False),
        sa.Column("content_hash", sa.String(80), nullable=True),
        sa.Column(
            "captured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_evidence_company_id", "evidence", ["company_id"])
    op.create_index("ix_evidence_campaign_id", "evidence", ["campaign_id"])
    op.create_table(
        "problem_hypotheses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("analysis_version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.Float(), nullable=False),
        sa.Column("evidence_strength", sa.Float(), nullable=False),
        sa.Column("business_impact_hypothesis", sa.Text(), nullable=True),
        sa.Column("impact_confidence", sa.Float(), nullable=True),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_problem_hypotheses_company_id", "problem_hypotheses", ["company_id"])
    op.create_index("ix_problem_hypotheses_campaign_id", "problem_hypotheses", ["campaign_id"])
    op.create_table(
        "solution_recommendations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "service_catalog_item_id",
            sa.Uuid(),
            sa.ForeignKey("service_catalog_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("problem_ids", sa.JSON(), nullable=False),
        sa.Column("fit_score", sa.Float(), nullable=False),
        sa.Column("why_it_fits", sa.Text(), nullable=False),
        sa.Column("implementation_complexity", sa.String(40), nullable=False),
        sa.Column("integration_questions", sa.JSON(), nullable=False),
        sa.Column("sales_angle", sa.Text(), nullable=False),
        sa.Column("opening_message", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    for column in ("company_id", "campaign_id", "service_catalog_item_id"):
        op.create_index(
            f"ix_solution_recommendations_{column}", "solution_recommendations", [column]
        )
    op.create_table(
        "lead_scores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score_version", sa.String(40), nullable=False),
        sa.Column("base_score", sa.Float(), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("band", sa.String(40), nullable=False),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("top_reasons", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    for column in ("company_id", "campaign_id", "final_score", "band"):
        op.create_index(f"ix_lead_scores_{column}", "lead_scores", [column])
    op.create_table(
        "leads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("current_score_id", sa.Uuid(), sa.ForeignKey("lead_scores.id"), nullable=False),
        sa.Column(
            "primary_recommendation_id",
            sa.Uuid(),
            sa.ForeignKey("solution_recommendations.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.UniqueConstraint("campaign_id", "company_id", name="uq_lead_campaign_company"),
    )
    for column in ("workspace_id", "campaign_id", "company_id"):
        op.create_index(f"ix_leads_{column}", "leads", [column])
    op.create_table(
        "job_executions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("job_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("graph_run_id", sa.String(200), nullable=True),
        sa.Column("graph_thread_id", sa.String(200), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(300), nullable=False, unique=True),
        sa.Column("input_fingerprint", sa.String(80), nullable=False),
        sa.Column("worker_version", sa.String(40), nullable=False),
        sa.Column(
            "queued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
    )
    op.create_index("ix_job_executions_campaign_id", "job_executions", ["campaign_id"])
    op.create_index("ix_job_executions_status", "job_executions", ["status"])
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.JSON(), nullable=True),
        *timestamps(),
        sa.UniqueConstraint("campaign_id", "provider", name="uq_campaign_export_provider"),
    )
    op.create_index("ix_export_jobs_campaign_id", "export_jobs", ["campaign_id"])

    # Supabase exposes the public schema through its Data API. These backend-owned
    # tables intentionally have no anon/authenticated policies; the Python service
    # connects server-side and remains the only application access path.
    if op.get_bind().dialect.name == "postgresql":
        for table in (
            "workspaces",
            "service_catalog_items",
            "campaigns",
            "campaign_services",
            "companies",
            "company_locations",
            "provider_entities",
            "campaign_companies",
            "contact_points",
            "digital_assets",
            "evidence",
            "problem_hypotheses",
            "solution_recommendations",
            "lead_scores",
            "leads",
            "job_executions",
            "export_jobs",
        ):
            op.execute(sa.text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))


def downgrade() -> None:
    for table in (
        "export_jobs",
        "job_executions",
        "leads",
        "lead_scores",
        "solution_recommendations",
        "problem_hypotheses",
        "evidence",
        "digital_assets",
        "contact_points",
        "campaign_companies",
        "provider_entities",
        "company_locations",
        "companies",
    ):
        op.drop_table(table)
    pipeline_status.drop(op.get_bind(), checkfirst=True)
