from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PipelineStatus(StrEnum):
    DISCOVERED = "DISCOVERED"
    DUPLICATE = "DUPLICATE"
    FILTERED_OUT = "FILTERED_OUT"
    QUALIFIED_FOR_ENRICHMENT = "QUALIFIED_FOR_ENRICHMENT"
    ENRICHING = "ENRICHING"
    ENRICHMENT_FAILED = "ENRICHMENT_FAILED"
    QUALIFIED_FOR_AUDIT = "QUALIFIED_FOR_AUDIT"
    AUDITING = "AUDITING"
    AUDIT_FAILED = "AUDIT_FAILED"
    QUALIFIED_FOR_ANALYSIS = "QUALIFIED_FOR_ANALYSIS"
    ANALYZING = "ANALYZING"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    SCORED = "SCORED"
    READY = "READY"
    EXPORTED = "EXPORTED"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    canonical_name: Mapped[str] = mapped_column(String(300))
    normalized_name: Mapped[str] = mapped_column(String(300), index=True)
    primary_domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    company_type: Mapped[str | None] = mapped_column(String(100), nullable=True)


class CompanyLocation(TimestampMixin, Base):
    __tablename__ = "company_locations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    formatted_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(150), nullable=True)
    region: Mapped[str | None] = mapped_column(String(150), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_primary: Mapped[bool] = mapped_column(default=True)
    source_kind: Mapped[str] = mapped_column(String(80), default="fixture")


class ProviderEntity(Base):
    __tablename__ = "provider_entities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_entity_id", name="uq_provider_entity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(80))
    provider_entity_id: Mapped[str] = mapped_column(String(300))
    retention_class: Mapped[str] = mapped_column(String(80), default="provider_identifier")
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    provider_metadata: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class CampaignCompany(TimestampMixin, Base):
    __tablename__ = "campaign_companies"
    __table_args__ = (UniqueConstraint("campaign_id", "company_id", name="uq_campaign_company"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    pipeline_status: Mapped[PipelineStatus] = mapped_column(
        Enum(PipelineStatus), default=PipelineStatus.DISCOVERED, index=True
    )
    qualification_status: Mapped[str] = mapped_column(String(80), default="PENDING")
    qualification_reason: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    priority_order: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ContactPoint(TimestampMixin, Base):
    __tablename__ = "contact_points"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    value: Mapped[str] = mapped_column(Text)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(40), default="public_unverified")
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(default=False)


class DigitalAsset(TimestampMixin, Base):
    __tablename__ = "digital_assets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="active")
    asset_metadata: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(80))
    claim: Mapped[str] = mapped_column(Text)
    source_kind: Mapped[str] = mapped_column(String(80))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    observation_data: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float)
    retention_class: Mapped[str] = mapped_column(String(80))
    content_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProblemHypothesis(Base):
    __tablename__ = "problem_hypotheses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    analysis_version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[float] = mapped_column(Float)
    evidence_strength: Mapped[float] = mapped_column(Float)
    business_impact_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SolutionRecommendation(Base):
    __tablename__ = "solution_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    service_catalog_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_catalog_items.id", ondelete="CASCADE"), index=True
    )
    problem_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    fit_score: Mapped[float] = mapped_column(Float)
    why_it_fits: Mapped[str] = mapped_column(Text)
    implementation_complexity: Mapped[str] = mapped_column(String(40))
    integration_questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    sales_angle: Mapped[str] = mapped_column(Text)
    opening_message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LeadScore(Base):
    __tablename__ = "lead_scores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    score_version: Mapped[str] = mapped_column(String(40), default="v1")
    base_score: Mapped[float] = mapped_column(Float)
    final_score: Mapped[float] = mapped_column(Float, index=True)
    confidence: Mapped[float] = mapped_column(Float)
    band: Mapped[str] = mapped_column(String(40), index=True)
    dimensions: Mapped[dict[str, float]] = mapped_column(JSON)
    top_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("campaign_id", "company_id", name="uq_lead_campaign_company"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    current_score_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lead_scores.id"))
    primary_recommendation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("solution_recommendations.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(40), default="READY_TO_CONTACT")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class JobExecution(Base):
    __tablename__ = "job_executions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=True
    )
    job_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), index=True)
    graph_run_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    graph_thread_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(300), unique=True)
    input_fingerprint: Mapped[str] = mapped_column(String(80))
    worker_version: Mapped[str] = mapped_column(String(40), default="0.1.0")
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    metrics: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class ExportJob(Base):
    __tablename__ = "export_jobs"
    __table_args__ = (
        UniqueConstraint("campaign_id", "provider", name="uq_campaign_export_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40))
    external_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
