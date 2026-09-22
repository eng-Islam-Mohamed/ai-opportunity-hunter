from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign, ServiceCatalogItem, Workspace


class CampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_workspace(self, workspace_id: uuid.UUID) -> Workspace | None:
        return await self._session.get(Workspace, workspace_id)

    async def get_services(
        self, workspace_id: uuid.UUID, service_ids: list[uuid.UUID]
    ) -> list[ServiceCatalogItem]:
        result = await self._session.scalars(
            select(ServiceCatalogItem).where(
                ServiceCatalogItem.workspace_id == workspace_id,
                ServiceCatalogItem.id.in_(service_ids),
                ServiceCatalogItem.active.is_(True),
            )
        )
        return list(result)

    async def add_campaign(self, campaign: Campaign) -> Campaign:
        self._session.add(campaign)
        await self._session.flush()
        await self._session.refresh(campaign, attribute_names=["services"])
        return campaign

    async def get_campaign(self, campaign_id: uuid.UUID) -> Campaign | None:
        result = await self._session.scalar(
            select(Campaign)
            .options(selectinload(Campaign.services))
            .where(Campaign.id == campaign_id)
        )
        return result


class ServiceCatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, item: ServiceCatalogItem) -> ServiceCatalogItem:
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return item
