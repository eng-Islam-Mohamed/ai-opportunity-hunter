from __future__ import annotations

import csv
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import ExportJob
from app.schemas.opportunity import ExportRead
from app.services.leads import list_campaign_leads


async def export_campaign_csv(
    session: AsyncSession, campaign_id: uuid.UUID, export_directory: str
) -> ExportRead:
    job = await session.scalar(
        select(ExportJob).where(ExportJob.campaign_id == campaign_id, ExportJob.provider == "csv")
    )
    if job is None:
        job = ExportJob(campaign_id=campaign_id, provider="csv", status="RUNNING")
        session.add(job)
        await session.flush()
    leads = await list_campaign_leads(session, campaign_id)
    directory = Path(export_directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"campaign-{campaign_id}.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Priority",
                "Company",
                "Location",
                "Website",
                "Phone",
                "Main Problem",
                "Recommended Solution",
                "Score",
                "Band",
                "Confidence",
                "Sales Angle",
                "Status",
            ]
        )
        for index, lead in enumerate(leads, start=1):
            writer.writerow(
                [
                    index,
                    lead.company_name,
                    lead.location,
                    lead.website,
                    lead.phone,
                    lead.main_problem,
                    lead.recommended_solution,
                    lead.final_score,
                    lead.band,
                    lead.confidence,
                    lead.sales_angle,
                    lead.status,
                ]
            )
    job.status = "COMPLETED"
    job.external_id = str(path)
    job.external_url = path.as_uri()
    job.row_count = len(leads)
    await session.commit()
    return ExportRead(
        id=job.id,
        campaign_id=job.campaign_id,
        provider=job.provider,
        status=job.status,
        external_url=job.external_url,
        row_count=job.row_count,
    )
