from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign, ServiceCatalogItem
from app.repositories.campaign import CampaignRepository, ServiceCatalogRepository
from app.schemas.campaign import CampaignCreate, ServiceCatalogCreate


class DomainNotFoundError(Exception):
    pass


class DomainValidationError(Exception):
    pass


class CampaignService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = CampaignRepository(session)

    async def create(self, payload: CampaignCreate) -> Campaign:
        if await self._repository.get_workspace(payload.workspace_id) is None:
            raise DomainNotFoundError("Workspace not found")
        unique_ids = list(dict.fromkeys(payload.service_catalog_item_ids))
        services = await self._repository.get_services(payload.workspace_id, unique_ids)
        if len(services) != len(unique_ids):
            raise DomainValidationError(
                "One or more services are missing, inactive, or outside the workspace"
            )

        campaign = Campaign(
            workspace_id=payload.workspace_id,
            name=payload.name,
            target=payload.target.model_dump(mode="json"),
            limits=payload.limits.model_dump(mode="json"),
            qualification=payload.qualification.model_dump(mode="json"),
            analysis_preferences=payload.analysis_preferences.model_dump(mode="json"),
            export_config=payload.export.model_dump(mode="json"),
            progress={
                "requested": payload.limits.max_discovery_candidates,
                "discovered": 0,
                "analyzed": 0,
                "qualified": 0,
            },
            services=services,
        )
        await self._repository.add_campaign(campaign)
        await self._session.commit()
        return campaign

    async def get(self, campaign_id: uuid.UUID) -> Campaign:
        campaign = await self._repository.get_campaign(campaign_id)
        if campaign is None:
            raise DomainNotFoundError("Campaign not found")
        return campaign

    async def list(self, workspace_id: uuid.UUID) -> list[Campaign]:
        return list(
            await self._session.scalars(
                select(Campaign)
                .options(selectinload(Campaign.services))
                .where(Campaign.workspace_id == workspace_id)
                .order_by(Campaign.created_at.desc())
            )
        )


class ServiceCatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._campaign_repository = CampaignRepository(session)
        self._repository = ServiceCatalogRepository(session)

    async def create(self, payload: ServiceCatalogCreate) -> ServiceCatalogItem:
        if await self._campaign_repository.get_workspace(payload.workspace_id) is None:
            raise DomainNotFoundError("Workspace not found")
        item = ServiceCatalogItem(**payload.model_dump())
        await self._repository.add(item)
        await self._session.commit()
        return item
