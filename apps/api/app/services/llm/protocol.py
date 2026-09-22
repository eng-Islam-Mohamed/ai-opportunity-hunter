from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class LLMProvider(Protocol):
    async def generate_structured(
        self,
        *,
        task: str,
        system_prompt: str,
        user_payload: dict[str, object],
        response_model: type[ResponseT],
        temperature: float = 0.1,
    ) -> ResponseT: ...
