from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.models.campaign import Campaign, CampaignStatus, ServiceCatalogItem
from app.models.opportunity import (
    CampaignCompany,
    Company,
    CompanyLocation,
    ContactPoint,
    DigitalAsset,
    Evidence,
    JobExecution,
    Lead,
    LeadScore,
    PipelineStatus,
    ProblemHypothesis,
    ProviderEntity,
    SolutionRecommendation,
)
from app.schemas.campaign import SearchTarget
from app.schemas.opportunity import DiscoveredBusiness, ProblemAnalysis
from app.services.analysis import (
    analyze_evidence_deterministically,
    sales_copy,
    select_service,
)
from app.services.discovery import FixtureDiscoveryProvider, GooglePlacesDiscoveryProvider
from app.services.discovery.protocol import DiscoveryProvider
from app.services.llm.openrouter import LLMProviderError, OpenRouterLLMProvider
from app.services.normalization import (
    canonicalize_url,
    domain_from_url,
    normalize_name,
    normalize_phone,
)
from app.services.scoring import ScoreDimensions, calculate_score

logger = logging.getLogger(__name__)


class CampaignPipeline:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def run(self, campaign_id: uuid.UUID) -> dict[str, object]:
        campaign = await self._session.scalar(
            select(Campaign)
            .options(selectinload(Campaign.services))
            .where(Campaign.id == campaign_id)
        )
        if campaign is None:
            raise ValueError("Campaign not found")
        job = await self._get_or_create_job(campaign)
        if job.status == "COMPLETED":
            return job.metrics
        await self._clear_partial_results(campaign.id)
        job.status = "RUNNING"
        job.attempt += 1 if job.started_at else 0
        job.started_at = datetime.now(UTC)
        campaign.status = CampaignStatus.DISCOVERING
        await self._session.commit()

        try:
            target = SearchTarget.model_validate(campaign.target)
            raw_limit = campaign.limits["max_discovery_candidates"]
            if not isinstance(raw_limit, int):
                raise ValueError("max_discovery_candidates must be an integer")
            discovered = await self._provider().search(target, limit=raw_limit)
            campaign.progress = {
                "requested": raw_limit,
                "discovered": len(discovered),
                "analyzed": 0,
                "qualified": 0,
            }
            campaign.status = CampaignStatus.NORMALIZING
            await self._session.commit()

            analyzed = 0
            qualified = 0
            raw_llm_limit = campaign.limits.get("max_llm_analyses", 0)
            if not isinstance(raw_llm_limit, int):
                raise ValueError("max_llm_analyses must be an integer")
            for candidate in discovered:
                company, is_new = await self._persist_candidate(campaign, candidate)
                if not is_new:
                    existing_link = await self._session.scalar(
                        select(CampaignCompany).where(
                            CampaignCompany.campaign_id == campaign.id,
                            CampaignCompany.company_id == company.id,
                        )
                    )
                    if existing_link:
                        continue
                link = CampaignCompany(
                    campaign_id=campaign.id,
                    company_id=company.id,
                    pipeline_status=PipelineStatus.QUALIFIED_FOR_AUDIT,
                    qualification_status="QUALIFIED",
                    qualification_reason={"source": candidate.provider},
                )
                self._session.add(link)
                evidence = self._build_evidence(campaign.id, company.id, candidate)
                self._session.add_all(evidence)
                await self._session.flush()
                link.pipeline_status = PipelineStatus.ANALYZING
                problems = await self._analyze(
                    company,
                    evidence,
                    analyzed,
                    max_llm_analyses=raw_llm_limit,
                )
                analyzed += 1
                lead_created = await self._persist_analysis(
                    campaign, company, campaign.services, problems
                )
                if lead_created:
                    qualified += 1
                    link.pipeline_status = PipelineStatus.READY
                else:
                    link.pipeline_status = PipelineStatus.FILTERED_OUT
                    link.qualification_status = "NO_SERVICE_MATCH"
                await self._session.flush()

            campaign.status = CampaignStatus.READY_FOR_REVIEW
            campaign.progress = {
                "requested": raw_limit,
                "discovered": len(discovered),
                "analyzed": analyzed,
                "qualified": qualified,
            }
            job.status = "COMPLETED"
            job.completed_at = datetime.now(UTC)
            job.metrics = dict(campaign.progress)
            await self._session.commit()
            return job.metrics
        except Exception as exc:
            await self._session.rollback()
            campaign = await self._session.get(Campaign, campaign_id)
            recovered_job = await self._session.scalar(
                select(JobExecution).where(
                    JobExecution.idempotency_key == f"campaign:{campaign_id}:v1"
                )
            )
            if campaign:
                campaign.status = CampaignStatus.FAILED
                campaign.error_summary = {"type": type(exc).__name__, "message": str(exc)[:500]}
            if recovered_job:
                recovered_job.status = "FAILED"
                recovered_job.completed_at = datetime.now(UTC)
                recovered_job.error = {
                    "type": type(exc).__name__,
                    "message": str(exc)[:500],
                }
            await self._session.commit()
            raise

    def _provider(self) -> DiscoveryProvider:
        if self._settings.discovery_provider == "google_places":
            if not self._settings.google_maps_api_key:
                raise ValueError("GOOGLE_MAPS_API_KEY is required for Google Places discovery")
            return GooglePlacesDiscoveryProvider(self._settings.google_maps_api_key)
        return FixtureDiscoveryProvider()

    async def _get_or_create_job(self, campaign: Campaign) -> JobExecution:
        key = f"campaign:{campaign.id}:v1"
        job = await self._session.scalar(
            select(JobExecution).where(JobExecution.idempotency_key == key)
        )
        if job is None:
            fingerprint = hashlib.sha256(
                json.dumps(
                    {"target": campaign.target, "limits": campaign.limits}, sort_keys=True
                ).encode()
            ).hexdigest()
            job = JobExecution(
                campaign_id=campaign.id,
                job_type="campaign_pipeline",
                status="QUEUED",
                graph_thread_id=f"campaign:{campaign.id}",
                graph_run_id=str(uuid.uuid4()),
                idempotency_key=key,
                input_fingerprint=fingerprint,
                metrics={},
            )
            self._session.add(job)
            await self._session.flush()
        return job

    async def _clear_partial_results(self, campaign_id: uuid.UUID) -> None:
        for model in (
            Lead,
            LeadScore,
            SolutionRecommendation,
            ProblemHypothesis,
            Evidence,
            CampaignCompany,
        ):
            await self._session.execute(delete(model).where(model.campaign_id == campaign_id))

    async def _persist_candidate(
        self, campaign: Campaign, candidate: DiscoveredBusiness
    ) -> tuple[Company, bool]:
        provider_entity = await self._session.scalar(
            select(ProviderEntity).where(
                ProviderEntity.provider == candidate.provider,
                ProviderEntity.provider_entity_id == candidate.provider_entity_id,
            )
        )
        if provider_entity:
            company = await self._session.get(Company, provider_entity.company_id)
            if company is None:
                raise RuntimeError("Provider entity points to a missing company")
            return company, False

        domain = domain_from_url(candidate.website)
        company = None
        if domain:
            company = await self._session.scalar(
                select(Company).where(Company.primary_domain == domain).limit(1)
            )
        is_new = company is None
        if company is None:
            company = Company(
                canonical_name=candidate.name,
                normalized_name=normalize_name(candidate.name),
                primary_domain=domain,
                company_type=str(campaign.target.get("query", "business")),
            )
            self._session.add(company)
            await self._session.flush()
            self._session.add(
                CompanyLocation(
                    company_id=company.id,
                    formatted_address=candidate.address,
                    city=candidate.city,
                    region=candidate.region,
                    country_code=candidate.country_code,
                    latitude=candidate.latitude,
                    longitude=candidate.longitude,
                    source_kind=candidate.provider,
                )
            )
            canonical_url = canonicalize_url(candidate.website)
            if canonical_url:
                self._session.add(
                    DigitalAsset(
                        company_id=company.id,
                        kind="website",
                        url=candidate.website or canonical_url,
                        canonical_url=canonical_url,
                        asset_metadata={},
                    )
                )
            for kind, value in (("phone", candidate.phone), ("email", candidate.email)):
                if value:
                    self._session.add(
                        ContactPoint(
                            company_id=company.id,
                            kind=kind,
                            value=value,
                            normalized_value=normalize_phone(value)
                            if kind == "phone"
                            else value.casefold(),
                            verification_status="public_unverified",
                            source_url=canonical_url,
                            is_primary=True,
                        )
                    )
        self._session.add(
            ProviderEntity(
                company_id=company.id,
                provider=candidate.provider,
                provider_entity_id=candidate.provider_entity_id,
                provider_metadata={
                    "rating": candidate.rating,
                    "review_count": candidate.review_count,
                },
            )
        )
        await self._session.flush()
        return company, is_new

    @staticmethod
    def _build_evidence(
        campaign_id: uuid.UUID, company_id: uuid.UUID, candidate: DiscoveredBusiness
    ) -> list[Evidence]:
        website_detected = bool(candidate.website)
        data = {"website_detected": website_detected, **candidate.signals}
        if not website_detected:
            claim = (
                "No verified first-party website was present in the configured discovery source."
            )
        elif candidate.signals.get("booking_link_detected") is False:
            claim = "No self-service booking link was detected in the audited public conversion signals."
        else:
            claim = "A first-party website and its public conversion signals were evaluated."
        return [
            Evidence(
                company_id=company_id,
                campaign_id=campaign_id,
                evidence_type="website_observation",
                claim=claim,
                source_kind="first_party_website" if website_detected else "provider_business_data",
                source_url=canonicalize_url(candidate.website),
                source_title=candidate.name,
                observation_data=data,
                confidence=0.94 if candidate.provider == "fixture" else 0.86,
                retention_class="derived_intelligence",
                content_hash=hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest(),
            )
        ]

    async def _analyze(
        self,
        company: Company,
        evidence: list[Evidence],
        analyzed_count: int,
        *,
        max_llm_analyses: int,
    ) -> ProblemAnalysis:
        use_llm = (
            self._settings.enable_llm_analysis
            and self._settings.llm_provider == "openrouter"
            and self._settings.llm_api_key is not None
            and analyzed_count < max_llm_analyses
        )
        if not use_llm:
            return analyze_evidence_deterministically(evidence)
        api_key = self._settings.llm_api_key
        if api_key is None:
            return analyze_evidence_deterministically(evidence)
        provider = OpenRouterLLMProvider(
            api_key=api_key,
            model=self._settings.llm_model_analysis,
            base_url=str(self._settings.llm_base_url),
            timeout_seconds=self._settings.llm_timeout_seconds,
        )
        try:
            return await provider.generate_structured(
                task="problem_analysis_v1",
                system_prompt=(
                    "You are an evidence-first business analyst. Identify at most three credible problems. "
                    "Every problem must cite supplied evidence IDs. Do not infer hidden internal systems."
                ),
                user_payload={
                    "company": {"id": str(company.id), "name": company.canonical_name},
                    "evidence": [
                        {
                            "id": str(item.id),
                            "claim": item.claim,
                            "observation_data": item.observation_data,
                            "confidence": item.confidence,
                        }
                        for item in evidence
                    ],
                    "analysis_sequence": analyzed_count,
                },
                response_model=ProblemAnalysis,
            )
        except LLMProviderError as exc:
            logger.warning(
                "llm_analysis_fallback",
                extra={"company_id": str(company.id), "error_type": type(exc).__name__},
            )
            return analyze_evidence_deterministically(evidence)

    async def _persist_analysis(
        self,
        campaign: Campaign,
        company: Company,
        services: list[ServiceCatalogItem],
        analysis: ProblemAnalysis,
    ) -> bool:
        if not analysis.problems:
            return False
        problem_contract = analysis.problems[0]
        problem = ProblemHypothesis(
            company_id=company.id,
            campaign_id=campaign.id,
            title=problem_contract.title,
            category=problem_contract.category,
            description=problem_contract.description,
            severity=problem_contract.severity,
            evidence_strength=problem_contract.evidence_strength,
            business_impact_hypothesis=problem_contract.business_impact_hypothesis,
            impact_confidence=problem_contract.impact_confidence,
            limitations=problem_contract.limitations,
            evidence_ids=problem_contract.evidence_ids,
        )
        self._session.add(problem)
        await self._session.flush()
        match = select_service(problem_contract, services)
        if match is None:
            return False
        service, fit = match
        angle, opening = sales_copy(company.canonical_name, problem_contract, service)
        recommendation = SolutionRecommendation(
            company_id=company.id,
            campaign_id=campaign.id,
            service_catalog_item_id=service.id,
            problem_ids=[str(problem.id)],
            fit_score=fit,
            why_it_fits=(
                f"{service.title} supports the observed {problem_contract.category.replace('_', ' ')} "
                "problem and the evidence meets the service threshold."
            ),
            implementation_complexity="medium",
            integration_questions=[
                "Which system currently receives public inquiries?",
                "Which integrations are available for a limited pilot?",
            ],
            sales_angle=angle,
            opening_message=opening,
        )
        self._session.add(recommendation)
        await self._session.flush()
        confidence = min(1.0, problem_contract.evidence_strength * 0.95)
        score_result = calculate_score(
            ScoreDimensions(
                problem_severity=problem_contract.severity * 100,
                solution_fit=fit * 100,
                evidence_strength=problem_contract.evidence_strength * 100,
                business_value_potential=75,
                contactability=85,
                implementation_feasibility=78,
                urgency_signal=50,
                company_capacity_proxy=60,
            ),
            confidence=confidence,
        )
        score = LeadScore(
            company_id=company.id,
            campaign_id=campaign.id,
            base_score=score_result.base_score,
            final_score=score_result.final_score,
            confidence=score_result.confidence,
            band=score_result.band,
            dimensions=score_result.dimensions.model_dump(),
            top_reasons=[
                "Evidence-backed public digital problem",
                "Direct service-to-problem compatibility",
                "Verified public contact channel",
            ],
        )
        self._session.add(score)
        await self._session.flush()
        self._session.add(
            Lead(
                workspace_id=campaign.workspace_id,
                campaign_id=campaign.id,
                company_id=company.id,
                current_score_id=score.id,
                primary_recommendation_id=recommendation.id,
            )
        )
        return True
