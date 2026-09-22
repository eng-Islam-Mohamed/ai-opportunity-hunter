from __future__ import annotations

from typing import Protocol

from app.schemas.campaign import SearchTarget
from app.schemas.opportunity import DiscoveredBusiness


class DiscoveryProvider(Protocol):
    async def search(self, target: SearchTarget, *, limit: int) -> list[DiscoveredBusiness]: ...
