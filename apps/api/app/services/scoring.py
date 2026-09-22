from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ScoreDimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_severity: float = Field(ge=0, le=100)
    solution_fit: float = Field(ge=0, le=100)
    evidence_strength: float = Field(ge=0, le=100)
    business_value_potential: float = Field(ge=0, le=100)
    contactability: float = Field(ge=0, le=100)
    implementation_feasibility: float = Field(ge=0, le=100)
    urgency_signal: float = Field(ge=0, le=100)
    company_capacity_proxy: float = Field(ge=0, le=100)


class ScoreResult(BaseModel):
    base_score: float
    final_score: float
    confidence: float
    band: str
    dimensions: ScoreDimensions


DEFAULT_WEIGHTS: dict[str, float] = {
    "problem_severity": 0.20,
    "solution_fit": 0.20,
    "evidence_strength": 0.20,
    "business_value_potential": 0.15,
    "contactability": 0.10,
    "implementation_feasibility": 0.10,
    "urgency_signal": 0.03,
    "company_capacity_proxy": 0.02,
}


def calculate_score(
    dimensions: ScoreDimensions,
    *,
    confidence: float,
    weights: dict[str, float] | None = None,
) -> ScoreResult:
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    effective_weights = weights or DEFAULT_WEIGHTS
    if set(effective_weights) != set(DEFAULT_WEIGHTS):
        raise ValueError("weights must include exactly the supported score dimensions")
    if abs(sum(effective_weights.values()) - 1.0) > 1e-9:
        raise ValueError("weights must total 1.0")

    values = dimensions.model_dump()
    base_score = sum(values[key] * weight for key, weight in effective_weights.items())
    final_score = base_score * (0.75 + 0.25 * confidence)
    rounded = round(final_score, 2)
    if rounded >= 90:
        band = "HOT"
    elif rounded >= 80:
        band = "STRONG"
    elif rounded >= 70:
        band = "QUALIFIED"
    elif rounded >= 55:
        band = "REVIEW"
    else:
        band = "LOW_PRIORITY"
    return ScoreResult(
        base_score=round(base_score, 2),
        final_score=rounded,
        confidence=confidence,
        band=band,
        dimensions=dimensions,
    )
