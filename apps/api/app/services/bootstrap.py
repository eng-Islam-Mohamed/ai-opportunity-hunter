from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import ServiceCatalogItem, Workspace
from app.schemas.opportunity import BootstrapResponse

DEFAULT_SERVICES = [
    {
        "slug": "ai_whatsapp_booking",
        "title": "AI WhatsApp Booking Agent",
        "description": "Inquiry handling, qualification, appointment requests, scheduling and reminders.",
        "supported_problem_categories": [
            "booking",
            "customer_support",
            "lead_follow_up",
            "customer_self_service",
        ],
        "ideal_customer_profiles": ["dental_clinic", "medical_clinic", "salon", "hotel"],
    },
    {
        "slug": "website_redesign",
        "title": "Website Redesign",
        "description": "Conversion-focused responsive website and public customer journey improvements.",
        "supported_problem_categories": [
            "website_ux",
            "mobile_ux",
            "website_performance",
            "local_conversion",
        ],
        "ideal_customer_profiles": ["local_business", "clinic", "restaurant", "real_estate_agency"],
    },
    {
        "slug": "crm_automation",
        "title": "CRM Automation",
        "description": "Structured lead capture, routing, follow-up and pipeline automation.",
        "supported_problem_categories": [
            "lead_capture",
            "lead_follow_up",
            "operational_automation",
            "form_friction",
        ],
        "ideal_customer_profiles": ["service_business", "clinic", "real_estate_agency"],
    },
    {
        "slug": "seo_optimization",
        "title": "SEO Optimization",
        "description": "Technical SEO and local search foundation improvements grounded in audit findings.",
        "supported_problem_categories": ["seo_basics", "local_conversion", "website_performance"],
        "ideal_customer_profiles": ["local_business", "clinic", "restaurant", "hotel"],
    },
]


async def bootstrap_workspace(
    session: AsyncSession, name: str = "Default Workspace"
) -> BootstrapResponse:
    workspace = await session.scalar(select(Workspace).where(Workspace.name == name).limit(1))
    created = workspace is None
    if workspace is None:
        workspace = Workspace(name=name)
        session.add(workspace)
        await session.flush()
    existing = list(
        await session.scalars(
            select(ServiceCatalogItem).where(ServiceCatalogItem.workspace_id == workspace.id)
        )
    )
    by_slug = {item.slug: item for item in existing}
    for definition in DEFAULT_SERVICES:
        if definition["slug"] not in by_slug:
            item = ServiceCatalogItem(workspace_id=workspace.id, **definition)
            session.add(item)
            by_slug[item.slug] = item
    await session.commit()
    return BootstrapResponse(
        workspace_id=workspace.id,
        service_ids=[item.id for item in by_slug.values()],
        created=created,
    )
