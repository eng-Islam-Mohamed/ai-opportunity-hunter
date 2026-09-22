import pytest
from app.schemas.opportunity import ProblemFinding
from pydantic import ValidationError


def test_problem_contract_rejects_free_form_category_and_missing_limitations() -> None:
    with pytest.raises(ValidationError):
        ProblemFinding.model_validate(
            {
                "title": "No verified website",
                "category": "Online Presence",
                "description": "No website was returned by the configured source.",
                "evidence_ids": ["evidence-1"],
                "severity": 0.7,
                "evidence_strength": 0.86,
                "limitations": [],
            }
        )
