import uuid

import pytest
from app.schemas.campaign import CampaignCreate
from pydantic import ValidationError


def test_campaign_limits_must_narrow() -> None:
    with pytest.raises(ValidationError, match="limits must narrow"):
        CampaignCreate.model_validate(
            {
                "workspace_id": str(uuid.uuid4()),
                "name": "Dubai clinics",
                "target": {
                    "query": "dental clinic",
                    "location_text": "Dubai Marina, UAE",
                    "country_code": "AE",
                },
                "limits": {
                    "max_discovery_candidates": 10,
                    "max_enriched_candidates": 20,
                    "max_full_audits": 5,
                    "max_llm_analyses": 5,
                },
                "service_catalog_item_ids": [str(uuid.uuid4())],
            }
        )
