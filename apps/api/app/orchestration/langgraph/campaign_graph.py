from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.orchestration.langgraph.state import CampaignGraphState
from app.services.pipeline import CampaignPipeline


async def load_campaign(state: CampaignGraphState) -> CampaignGraphState:
    return {**state, "status": "loaded", "error": None}


async def _run_pipeline(campaign_id: str) -> dict[str, object]:
    async with SessionFactory() as session:
        return await CampaignPipeline(session, get_settings()).run(uuid.UUID(campaign_id))


async def finalize_campaign(state: CampaignGraphState) -> CampaignGraphState:
    return {**state, "status": "completed"}


def build_campaign_graph(
    checkpointer: Any = None,
    pipeline_runner: Callable[[str], Awaitable[dict[str, object]]] | None = None,
) -> Any:
    runner = pipeline_runner or _run_pipeline

    async def execute_campaign(state: CampaignGraphState) -> CampaignGraphState:
        metrics = await runner(state["campaign_id"])
        return {**state, "status": "ready_for_review", "metrics": metrics}

    builder = StateGraph(CampaignGraphState)
    builder.add_node("load_campaign", load_campaign)
    builder.add_node("execute_campaign", execute_campaign)
    builder.add_node("finalize_campaign", finalize_campaign)
    builder.add_edge(START, "load_campaign")
    builder.add_edge("load_campaign", "execute_campaign")
    builder.add_edge("execute_campaign", "finalize_campaign")
    builder.add_edge("finalize_campaign", END)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())
