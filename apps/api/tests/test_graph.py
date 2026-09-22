import uuid

import pytest
from app.orchestration.langgraph.campaign_graph import build_campaign_graph
from langgraph.checkpoint.memory import InMemorySaver


@pytest.mark.asyncio
async def test_campaign_graph_uses_stable_thread_and_checkpoints() -> None:
    campaign_id = str(uuid.uuid4())

    async def runner(value: str) -> dict[str, object]:
        assert value == campaign_id
        return {"discovered": 10, "qualified": 7}

    graph = build_campaign_graph(InMemorySaver(), runner)
    config = {"configurable": {"thread_id": f"campaign:{campaign_id}"}}
    result = await graph.ainvoke({"campaign_id": campaign_id, "status": "queued"}, config)
    state = await graph.aget_state(config)
    assert result["status"] == "completed"
    assert result["metrics"]["qualified"] == 7
    assert state.values["campaign_id"] == campaign_id
