from __future__ import annotations

import os
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DatabaseSession, get_current_user
from app.core.config import get_settings
from app.models.campaign import Campaign, CampaignStatus, DailyCampaignUsage, Workspace
from app.models.opportunity import JobExecution, Lead
from app.schemas.campaign import (
    CampaignCreate,
    CampaignRead,
    ServiceCatalogCreate,
    ServiceCatalogRead,
)
from app.schemas.opportunity import (
    BootstrapResponse,
    CampaignExecutionRead,
    ExportRead,
    LeadDetail,
    LeadListItem,
)
from app.services.bootstrap import bootstrap_workspace
from app.services.campaigns import (
    CampaignService,
    DomainNotFoundError,
    DomainValidationError,
    ServiceCatalogService,
)
from app.services.execution import execute_campaign, is_running, submit_campaign
from app.services.exports import export_campaign_csv
from app.services.google_sheets import export_campaign_google_sheets
from app.services.leads import get_lead_detail, list_campaign_leads

router = APIRouter(prefix="/api/v1", tags=["campaigns"], dependencies=[Depends(get_current_user)])


async def require_owned_workspace(
    session: DatabaseSession, workspace_id: uuid.UUID, user: CurrentUser
) -> Workspace:
    workspace = await session.get(Workspace, workspace_id)
    if workspace is None or workspace.owner_user_id != user.id:
        # Returning 404 avoids confirming another user's workspace identifier.
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


async def require_owned_campaign(
    session: DatabaseSession, campaign_id: uuid.UUID, user: CurrentUser
) -> Campaign:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await require_owned_workspace(session, campaign.workspace_id, user)
    return campaign


@router.post("/bootstrap", response_model=BootstrapResponse)
async def bootstrap(session: DatabaseSession, user: CurrentUser) -> BootstrapResponse:
    return await bootstrap_workspace(session, user.id, name=f"{user.email.split('@')[0]} Workspace")


@router.post(
    "/service-catalog",
    response_model=ServiceCatalogRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_service(
    payload: ServiceCatalogCreate, session: DatabaseSession, user: CurrentUser
) -> ServiceCatalogRead:
    await require_owned_workspace(session, payload.workspace_id, user)
    try:
        item = await ServiceCatalogService(session).create(payload)
    except DomainNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ServiceCatalogRead.model_validate(item)


@router.post("/campaigns", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate, session: DatabaseSession, user: CurrentUser
) -> CampaignRead:
    await require_owned_workspace(session, payload.workspace_id, user)
    try:
        campaign = await CampaignService(session).create(payload)
    except DomainNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CampaignRead.model_validate(campaign)


@router.get("/campaigns", response_model=list[CampaignRead])
async def list_campaigns(
    session: DatabaseSession, workspace_id: Annotated[uuid.UUID, Query()], user: CurrentUser
) -> list[CampaignRead]:
    await require_owned_workspace(session, workspace_id, user)
    campaigns = await CampaignService(session).list(workspace_id)
    return [CampaignRead.model_validate(campaign) for campaign in campaigns]


@router.get("/campaigns/{campaign_id}", response_model=CampaignRead)
async def get_campaign(
    campaign_id: uuid.UUID, session: DatabaseSession, user: CurrentUser
) -> CampaignRead:
    campaign = await require_owned_campaign(session, campaign_id, user)
    return CampaignRead.model_validate(campaign)


@router.post(
    "/campaigns/{campaign_id}/start",
    response_model=CampaignExecutionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_campaign(
    campaign_id: uuid.UUID, session: DatabaseSession, user: CurrentUser
) -> CampaignExecutionRead:
    campaign = await require_owned_campaign(session, campaign_id, user)
    if is_running(campaign_id):
        raise HTTPException(status_code=409, detail="Campaign is already running")
    usage = await session.scalar(
        select(DailyCampaignUsage).where(
            DailyCampaignUsage.user_id == user.id, DailyCampaignUsage.usage_date == date.today()
        )
    )
    if usage is None:
        usage = DailyCampaignUsage(user_id=user.id, usage_date=date.today(), campaign_runs=0)
        session.add(usage)
    if usage.campaign_runs >= 5:
        raise HTTPException(status_code=429, detail="Daily limit reached. Try again tomorrow.")
    usage.campaign_runs += 1
    campaign.status = CampaignStatus.QUEUED
    await session.commit()
    if os.getenv("VERCEL") == "1":
        # Vercel Functions do not preserve in-memory asyncio tasks after the
        # HTTP response. Run the bounded campaign before responding so it is
        # not abandoned when the function instance is frozen.
        await execute_campaign(campaign_id)
    elif not submit_campaign(campaign_id):
        raise HTTPException(status_code=409, detail="Campaign is already running")
    return CampaignExecutionRead(
        campaign_id=campaign.id,
        status=campaign.status.value,
        graph_thread_id=f"campaign:{campaign.id}",
        progress=campaign.progress,
    )


@router.get("/campaigns/{campaign_id}/execution", response_model=CampaignExecutionRead)
async def campaign_execution(
    campaign_id: uuid.UUID, session: DatabaseSession, user: CurrentUser
) -> CampaignExecutionRead:
    campaign = await require_owned_campaign(session, campaign_id, user)
    job = await session.scalar(
        select(JobExecution)
        .where(JobExecution.campaign_id == campaign_id)
        .order_by(JobExecution.queued_at.desc())
        .limit(1)
    )
    return CampaignExecutionRead(
        campaign_id=campaign.id,
        status=campaign.status.value,
        graph_thread_id=job.graph_thread_id if job else None,
        progress=campaign.progress,
        error=campaign.error_summary,
    )


@router.post("/campaigns/{campaign_id}/cancel", response_model=CampaignExecutionRead)
async def cancel_campaign(
    campaign_id: uuid.UUID, session: DatabaseSession, user: CurrentUser
) -> CampaignExecutionRead:
    campaign = await require_owned_campaign(session, campaign_id, user)
    if is_running(campaign_id):
        raise HTTPException(
            status_code=409,
            detail="Active in-process execution cannot be force-cancelled safely; retry after it reaches a boundary",
        )
    campaign.status = CampaignStatus.CANCELLED
    await session.commit()
    return CampaignExecutionRead(
        campaign_id=campaign.id,
        status=campaign.status.value,
        progress=campaign.progress,
    )


@router.get("/campaigns/{campaign_id}/leads", response_model=list[LeadListItem])
async def campaign_leads(
    campaign_id: uuid.UUID, session: DatabaseSession, user: CurrentUser
) -> list[LeadListItem]:
    await require_owned_campaign(session, campaign_id, user)
    return await list_campaign_leads(session, campaign_id)


@router.get("/leads/{lead_id}", response_model=LeadDetail)
async def lead_detail(lead_id: uuid.UUID, session: DatabaseSession, user: CurrentUser) -> LeadDetail:
    lead = await session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    await require_owned_campaign(session, lead.campaign_id, user)
    result = await get_lead_detail(session, lead_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return result


@router.post("/campaigns/{campaign_id}/export/csv", response_model=ExportRead)
async def export_csv(campaign_id: uuid.UUID, session: DatabaseSession, user: CurrentUser) -> ExportRead:
    await require_owned_campaign(session, campaign_id, user)
    return await export_campaign_csv(session, campaign_id, get_settings().export_directory)


@router.post("/campaigns/{campaign_id}/export/google-sheets", response_model=ExportRead)
async def export_google_sheets(
    campaign_id: uuid.UUID, session: DatabaseSession, user: CurrentUser
) -> ExportRead:
    await require_owned_campaign(session, campaign_id, user)
    settings = get_settings()
    if (
        settings.google_service_account_json is None
        and settings.google_oauth_client_secrets_file is None
        and settings.google_oauth_token_json is None
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "Google Sheets export is not configured. Set GOOGLE_SERVICE_ACCOUNT_JSON "
                "or GOOGLE_OAUTH_CLIENT_SECRETS_FILE."
            ),
        )
    try:
        return await export_campaign_google_sheets(
            session,
            campaign_id,
            settings.google_service_account_json.get_secret_value()
            if settings.google_service_account_json
            else None,
            settings.google_sheets_user_email,
            settings.google_oauth_client_secrets_file,
            settings.google_oauth_token_file,
            settings.google_oauth_client_secrets_json.get_secret_value()
            if settings.google_oauth_client_secrets_json
            else None,
            settings.google_oauth_token_json.get_secret_value()
            if settings.google_oauth_token_json
            else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
