from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.campaign import CampaignStatus


class SearchTarget(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    location_text: str = Field(min_length=2, max_length=300)
    country_code: str = Field(min_length=2, max_length=2)
    language: str = Field(default="en", min_length=2, max_length=10)
    radius_meters: int | None = Field(default=None, ge=100, le=50_000)
    geo_polygon: list[list[float]] | None = None


class CampaignLimits(BaseModel):
    max_discovery_candidates: int = Field(default=150, ge=1, le=1000)
    max_enriched_candidates: int = Field(default=100, ge=1, le=500)
    max_full_audits: int = Field(default=60, ge=1, le=250)
    max_llm_analyses: int = Field(default=60, ge=0, le=250)

    @model_validator(mode="after")
    def validate_funnel(self) -> CampaignLimits:
        if not (
            self.max_discovery_candidates >= self.max_enriched_candidates >= self.max_full_audits
        ):
            raise ValueError("limits must narrow from discovery to enrichment to full audit")
        if self.max_llm_analyses > self.max_full_audits:
            raise ValueError("max_llm_analyses cannot exceed max_full_audits")
        return self


class QualificationConfig(BaseModel):
    minimum_rating: float | None = Field(default=None, ge=0, le=5)
    minimum_review_count: int | None = Field(default=None, ge=0)
    website_required: bool = False
    contactability_required: bool = True
    exclude_chains: bool = False


class AnalysisPreferences(BaseModel):
    languages: list[str] = Field(default_factory=lambda: ["en"])
    focus_categories: list[str] = Field(default_factory=list)


class ExportConfig(BaseModel):
    google_sheets_enabled: bool = False
    minimum_score: int = Field(default=70, ge=0, le=100)


class CampaignCreate(BaseModel):
    workspace_id: uuid.UUID
    name: str = Field(min_length=2, max_length=200)
    target: SearchTarget
    limits: CampaignLimits = Field(default_factory=CampaignLimits)
    service_catalog_item_ids: list[uuid.UUID] = Field(min_length=1)
    qualification: QualificationConfig = Field(default_factory=QualificationConfig)
    analysis_preferences: AnalysisPreferences = Field(default_factory=AnalysisPreferences)
    export: ExportConfig = Field(default_factory=ExportConfig)


class ServiceCatalogCreate(BaseModel):
    workspace_id: uuid.UUID
    slug: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$", max_length=120)
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10)
    supported_problem_categories: list[str] = Field(min_length=1)
    ideal_customer_profiles: list[str] = Field(default_factory=list)
    minimum_evidence_strength: float = Field(default=0.6, ge=0, le=1)


class ServiceCatalogRead(ServiceCatalogCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    active: bool
    created_at: datetime
    updated_at: datetime


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    status: CampaignStatus
    worker_backend: str
    target: dict[str, object]
    limits: dict[str, object]
    qualification: dict[str, object]
    analysis_preferences: dict[str, object]
    export_config: dict[str, object]
    progress: dict[str, object]
    services: list[ServiceCatalogRead]
    created_at: datetime
    updated_at: datetime
