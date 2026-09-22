from __future__ import annotations

from collections.abc import Sequence

from app.models.campaign import ServiceCatalogItem
from app.models.opportunity import Evidence
from app.schemas.opportunity import ProblemAnalysis, ProblemFinding


def analyze_evidence_deterministically(evidence: Sequence[Evidence]) -> ProblemAnalysis:
    problems: list[ProblemFinding] = []
    for item in evidence:
        data = item.observation_data
        if data.get("website_detected") is False:
            problems.append(
                ProblemFinding(
                    title="No verified first-party website",
                    category="website_ux",
                    description=(
                        "No first-party website was verified in the available discovery data, "
                        "which limits the public digital conversion path."
                    ),
                    evidence_ids=[str(item.id)],
                    severity=0.82,
                    evidence_strength=item.confidence,
                    business_impact_hypothesis=(
                        "Prospective customers may have fewer self-service ways to evaluate services "
                        "or submit an inquiry."
                    ),
                    impact_confidence=0.68,
                    limitations=["A website could exist but be absent from the configured source."],
                )
            )
        elif data.get("booking_link_detected") is False:
            problems.append(
                ProblemFinding(
                    title="Contact-dependent appointment journey",
                    category="booking",
                    description=(
                        "No self-service booking path was detected in the audited public conversion signals."
                    ),
                    evidence_ids=[str(item.id)],
                    severity=0.76,
                    evidence_strength=item.confidence,
                    business_impact_hypothesis=(
                        "Prospective customers outside staffed response hours may experience friction "
                        "before confirming an appointment."
                    ),
                    impact_confidence=0.7,
                    limitations=["Internal scheduling processes are not visible publicly."],
                )
            )
        performance_score = data.get("performance_score", 100)
        if isinstance(performance_score, (int, float)) and performance_score < 60:
            problems.append(
                ProblemFinding(
                    title="Slow public website experience",
                    category="website_performance",
                    description="The deterministic audit recorded a performance score below 60/100.",
                    evidence_ids=[str(item.id)],
                    severity=0.64,
                    evidence_strength=item.confidence,
                    business_impact_hypothesis="Slow pages may add friction to mobile inquiry journeys.",
                    impact_confidence=0.65,
                    limitations=[
                        "The fixture score is a lab-style signal, not a revenue measurement."
                    ],
                )
            )
        if len(problems) >= 3:
            break
    return ProblemAnalysis(problems=problems[:3])


def select_service(
    problem: ProblemFinding, services: Sequence[ServiceCatalogItem]
) -> tuple[ServiceCatalogItem, float] | None:
    candidates = [
        service
        for service in services
        if problem.category in service.supported_problem_categories
        and problem.evidence_strength >= float(service.minimum_evidence_strength)
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            problem.category in item.supported_problem_categories,
            -float(item.minimum_evidence_strength),
        ),
        reverse=True,
    )
    service = candidates[0]
    fit = min(0.98, 0.72 + problem.evidence_strength * 0.24)
    return service, round(fit, 3)


def sales_copy(
    company_name: str, problem: ProblemFinding, service: ServiceCatalogItem
) -> tuple[str, str]:
    angle = (
        f"Offer {company_name} a focused {service.title} pilot addressing the observed "
        f"{problem.category.replace('_', ' ')} friction, with success criteria agreed before rollout."
    )
    opening = (
        f"Hello, I reviewed {company_name}'s public digital journey and noticed that "
        f"{problem.description[0].lower() + problem.description[1:]} I build {service.title.lower()} "
        "workflows and prepared a short, evidence-based outline of where one could fit."
    )
    return angle, opening
