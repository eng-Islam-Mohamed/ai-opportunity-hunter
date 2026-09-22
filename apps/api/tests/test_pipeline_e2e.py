from pathlib import Path

import pytest
from app.core.config import Settings
from app.db.base import Base
from app.models.opportunity import Evidence, Lead
from app.schemas.campaign import CampaignCreate
from app.services.bootstrap import bootstrap_workspace
from app.services.campaigns import CampaignService
from app.services.exports import export_campaign_csv
from app.services.pipeline import CampaignPipeline
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_fixture_campaign_runs_end_to_end_and_exports_idempotently(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        discovery_provider="fixture",
        llm_provider="fixture",
        enable_llm_analysis=False,
        export_directory=str(tmp_path / "exports"),
    )
    async with session_factory() as session:
        bootstrap = await bootstrap_workspace(session)
        campaign = await CampaignService(session).create(
            CampaignCreate.model_validate(
                {
                    "workspace_id": str(bootstrap.workspace_id),
                    "name": "Dubai Dental Fixture Campaign",
                    "target": {
                        "query": "dental clinic",
                        "location_text": "Dubai Marina, Dubai, UAE",
                        "country_code": "AE",
                    },
                    "limits": {
                        "max_discovery_candidates": 10,
                        "max_enriched_candidates": 10,
                        "max_full_audits": 10,
                        "max_llm_analyses": 10,
                    },
                    "service_catalog_item_ids": [str(value) for value in bootstrap.service_ids],
                }
            )
        )
        first = await CampaignPipeline(session, settings).run(campaign.id)
        second = await CampaignPipeline(session, settings).run(campaign.id)
        lead_count = await session.scalar(
            select(func.count()).select_from(Lead).where(Lead.campaign_id == campaign.id)
        )
        evidence_count = await session.scalar(
            select(func.count()).select_from(Evidence).where(Evidence.campaign_id == campaign.id)
        )
        export = await export_campaign_csv(session, campaign.id, settings.export_directory)
        repeated_export = await export_campaign_csv(session, campaign.id, settings.export_directory)

    assert first == second
    assert first["discovered"] == 10
    assert lead_count and lead_count >= 7
    assert evidence_count == 10
    assert export.row_count == lead_count
    assert repeated_export.id == export.id
    assert export.external_url is not None
    await engine.dispose()
