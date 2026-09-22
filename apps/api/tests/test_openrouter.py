import json

import httpx
import pytest
from app.services.llm.openrouter import OpenRouterLLMProvider
from pydantic import BaseModel, SecretStr


class Finding(BaseModel):
    title: str
    confidence: float


@pytest.mark.asyncio
async def test_openrouter_uses_strict_schema_without_exposing_key() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"title":"Booking friction","confidence":0.9}'}}
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenRouterLLMProvider(
        api_key=SecretStr("test-secret"),
        model="deepseek/deepseek-v4-pro",
        client=client,
    )
    result = await provider.generate_structured(
        task="problem_analysis",
        system_prompt="Use evidence only.",
        user_payload={"evidence": ["No booking link detected"]},
        response_model=Finding,
    )
    await client.aclose()

    assert result.title == "Booking friction"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "deepseek/deepseek-v4-pro"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["provider"]["require_parameters"] is True
    assert "test-secret" not in json.dumps(body)
