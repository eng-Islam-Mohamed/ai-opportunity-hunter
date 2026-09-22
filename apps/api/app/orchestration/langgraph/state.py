from __future__ import annotations

from typing import TypedDict


class CampaignGraphState(TypedDict, total=False):
    campaign_id: str
    status: str
    metrics: dict[str, object]
    error: dict[str, object] | None
