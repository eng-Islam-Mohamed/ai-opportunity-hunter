from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import ServiceCatalogItem
from app.models.opportunity import (
    Company,
    CompanyLocation,
    ContactPoint,
    DigitalAsset,
    Evidence,
    Lead,
    LeadScore,
    ProblemHypothesis,
    SolutionRecommendation,
)
from app.schemas.opportunity import EvidenceRead, LeadDetail, LeadListItem


async def list_campaign_leads(session: AsyncSession, campaign_id: uuid.UUID) -> list[LeadListItem]:
    problem_title = (
        select(ProblemHypothesis.title)
        .where(
            ProblemHypothesis.campaign_id == campaign_id,
            ProblemHypothesis.company_id == Company.id,
        )
        .order_by(ProblemHypothesis.severity.desc())
        .limit(1)
        .scalar_subquery()
    )
    website_url = (
        select(DigitalAsset.url)
        .where(DigitalAsset.company_id == Company.id, DigitalAsset.kind == "website")
        .limit(1)
        .scalar_subquery()
    )
    phone_value = (
        select(ContactPoint.value)
        .where(ContactPoint.company_id == Company.id, ContactPoint.kind == "phone")
        .limit(1)
        .scalar_subquery()
    )
    location_text = (
        select(CompanyLocation.formatted_address)
        .where(CompanyLocation.company_id == Company.id)
        .limit(1)
        .scalar_subquery()
    )
    rows = (
        await session.execute(
            select(
                Lead,
                Company,
                LeadScore,
                SolutionRecommendation,
                ServiceCatalogItem,
                problem_title.label("problem_title"),
                website_url.label("website_url"),
                phone_value.label("phone_value"),
                location_text.label("location_text"),
            )
            .join(Company, Company.id == Lead.company_id)
            .join(LeadScore, LeadScore.id == Lead.current_score_id)
            .outerjoin(
                SolutionRecommendation,
                SolutionRecommendation.id == Lead.primary_recommendation_id,
            )
            .outerjoin(
                ServiceCatalogItem,
                ServiceCatalogItem.id == SolutionRecommendation.service_catalog_item_id,
            )
            .where(Lead.campaign_id == campaign_id)
            .order_by(LeadScore.final_score.desc())
        )
    ).all()
    result: list[LeadListItem] = []
    for (
        lead,
        company,
        score,
        recommendation,
        service,
        problem,
        website,
        phone,
        location,
    ) in rows:
        result.append(
            LeadListItem(
                lead_id=lead.id,
                company_id=company.id,
                company_name=company.canonical_name,
                website=website,
                phone=phone,
                location=location,
                main_problem=problem,
                recommended_solution=service.title if service else None,
                final_score=score.final_score,
                band=score.band,
                confidence=score.confidence,
                sales_angle=recommendation.sales_angle if recommendation else None,
                status=lead.status,
            )
        )
    return result


async def get_lead_detail(session: AsyncSession, lead_id: uuid.UUID) -> LeadDetail | None:
    lead = await session.get(Lead, lead_id)
    if lead is None:
        return None
    items = await list_campaign_leads(session, lead.campaign_id)
    item = next((candidate for candidate in items if candidate.lead_id == lead_id), None)
    if item is None:
        return None
    score = await session.get(LeadScore, lead.current_score_id)
    recommendation = (
        await session.get(SolutionRecommendation, lead.primary_recommendation_id)
        if lead.primary_recommendation_id
        else None
    )
    evidence = list(
        await session.scalars(
            select(Evidence).where(
                Evidence.campaign_id == lead.campaign_id, Evidence.company_id == lead.company_id
            )
        )
    )
    problems = list(
        await session.scalars(
            select(ProblemHypothesis).where(
                ProblemHypothesis.campaign_id == lead.campaign_id,
                ProblemHypothesis.company_id == lead.company_id,
            )
        )
    )
    assert score is not None
    return LeadDetail(
        **item.model_dump(),
        opening_message=recommendation.opening_message if recommendation else None,
        score_dimensions=score.dimensions,
        top_reasons=score.top_reasons,
        evidence=[EvidenceRead.model_validate(value) for value in evidence],
        limitations=[value for problem in problems for value in problem.limitations],
    )
