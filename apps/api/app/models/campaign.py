from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CampaignStatus(StrEnum):
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    DISCOVERING = "DISCOVERING"
    NORMALIZING = "NORMALIZING"
    ENRICHING = "ENRICHING"
    AUDITING = "AUDITING"
    ANALYZING = "ANALYZING"
    SCORING = "SCORING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    EXPORTING = "EXPORTING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Workspace(TimestampMixin, Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))


class ServiceCatalogItem(TimestampMixin, Base):
    __tablename__ = "service_catalog_items"
    __table_args__ = (UniqueConstraint("workspace_id", "slug", name="uq_service_workspace_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    supported_problem_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    ideal_customer_profiles: Mapped[list[str]] = mapped_column(JSON, default=list)
    minimum_evidence_strength: Mapped[float] = mapped_column(Numeric(4, 3), default=0.6)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus), default=CampaignStatus.DRAFT, index=True
    )
    worker_backend: Mapped[str] = mapped_column(String(32), default="direct")
    execution_config: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    target: Mapped[dict[str, object]] = mapped_column(JSON)
    limits: Mapped[dict[str, object]] = mapped_column(JSON)
    qualification: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    analysis_preferences: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    export_config: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    progress: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    error_summary: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    services: Mapped[list[ServiceCatalogItem]] = relationship(
        secondary="campaign_services", lazy="selectin"
    )


class CampaignService(Base):
    __tablename__ = "campaign_services"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    service_catalog_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_catalog_items.id", ondelete="CASCADE"), primary_key=True
    )
