from __future__ import annotations

import asyncio
import logging
import uuid

from app.orchestration.langgraph import build_campaign_graph

logger = logging.getLogger(__name__)
_tasks: dict[uuid.UUID, asyncio.Task[object]] = {}
_graph = build_campaign_graph()


async def execute_campaign(campaign_id: uuid.UUID) -> None:
    try:
        await _graph.ainvoke(
            {"campaign_id": str(campaign_id), "status": "queued"},
            config={"configurable": {"thread_id": f"campaign:{campaign_id}"}},
        )
    except Exception:
        logger.exception("campaign_execution_failed", extra={"campaign_id": str(campaign_id)})
    finally:
        _tasks.pop(campaign_id, None)


def submit_campaign(campaign_id: uuid.UUID) -> bool:
    task = _tasks.get(campaign_id)
    if task and not task.done():
        return False
    _tasks[campaign_id] = asyncio.create_task(execute_campaign(campaign_id))
    return True


def is_running(campaign_id: uuid.UUID) -> bool:
    task = _tasks.get(campaign_id)
    return bool(task and not task.done())
