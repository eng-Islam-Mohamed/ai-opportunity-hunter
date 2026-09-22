import pytest
from app.services.scoring import ScoreDimensions, calculate_score


def test_explainable_score_and_confidence_penalty() -> None:
    dimensions = ScoreDimensions(
        problem_severity=86,
        solution_fit=96,
        evidence_strength=94,
        business_value_potential=83,
        contactability=92,
        implementation_feasibility=84,
        urgency_signal=50,
        company_capacity_proxy=70,
    )
    result = calculate_score(dimensions, confidence=0.9)
    assert result.base_score == 88.15
    assert result.final_score == 85.95
    assert result.band == "STRONG"
    assert result.dimensions.solution_fit == 96


def test_weights_must_total_one() -> None:
    dimensions = ScoreDimensions(
        problem_severity=50,
        solution_fit=50,
        evidence_strength=50,
        business_value_potential=50,
        contactability=50,
        implementation_feasibility=50,
        urgency_signal=50,
        company_capacity_proxy=50,
    )
    with pytest.raises(ValueError, match="total 1.0"):
        calculate_score(
            dimensions, confidence=1, weights=dict.fromkeys(dimensions.model_dump(), 0.2)
        )
