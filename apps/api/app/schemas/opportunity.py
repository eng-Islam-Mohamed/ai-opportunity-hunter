from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DiscoveredBusiness(BaseModel):
    provider: str
    provider_entity_id: str
    name: str
    address: str | None = None
    city: str | None = None
    region: str | None = None
    country_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    website: str | None = None
    phone: str | None = None
    email: str | None = None
    rating: float | None = None
    review_count: int | None = None
    signals: dict[str, object] = Field(default_factory=dict)


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evidence_type: str
    claim: str
    source_kind: str
    source_url: str | None
    observation_data: dict[str, object]
    confidence: float
    captured_at: datetime


class ProblemFinding(BaseModel):
    title: str = Field(min_length=4, max_length=300)
    category: Literal[
        "booking",
        "customer_support",
        "lead_capture",
        "lead_follow_up",
        "website_performance",
        "mobile_ux",
        "website_ux",
        "local_conversion",
        "seo_basics",
        "multilingual_experience",
        "trust_and_clarity",
        "form_friction",
        "reservation_flow",
        "ecommerce_conversion",
        "customer_self_service",
        "review_response_pattern",
        "operational_automation",
        "analytics_visibility",
        "other",
    ]
    description: str
    evidence_ids: list[str] = Field(min_length=1)
    severity: float = Field(ge=0, le=1)
    evidence_strength: float = Field(ge=0, le=1)
    business_impact_hypothesis: str | None = None
    impact_confidence: float | None = Field(default=None, ge=0, le=1)
    limitations: list[str] = Field(min_length=1)


class ProblemAnalysis(BaseModel):
    problems: list[ProblemFinding] = Field(max_length=3)


class LeadListItem(BaseModel):
    lead_id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    website: str | None
    phone: str | None
    location: str | None
    main_problem: str | None
    recommended_solution: str | None
    final_score: float
    band: str
    confidence: float
    sales_angle: str | None
    status: str


class LeadDetail(LeadListItem):
    opening_message: str | None
    score_dimensions: dict[str, float]
    top_reasons: list[str]
    evidence: list[EvidenceRead]
    limitations: list[str]


class CampaignExecutionRead(BaseModel):
    campaign_id: uuid.UUID
    status: str
    graph_thread_id: str | None = None
    progress: dict[str, object]
    error: dict[str, object] | None = None


class BootstrapResponse(BaseModel):
    workspace_id: uuid.UUID
    service_ids: list[uuid.UUID]
    created: bool


class ExportRead(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    provider: str
    status: str
    external_url: str | None
    row_count: int
