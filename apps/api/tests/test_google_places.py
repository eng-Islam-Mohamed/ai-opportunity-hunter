from __future__ import annotations

from typing import Any

import pytest
from app.schemas.campaign import SearchTarget
from app.services.discovery.google_places import GooglePlacesDiscoveryProvider
from pydantic import SecretStr


class FakePlacesResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class FakePlacesClient:
    payloads: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []

    def __init__(self, **_: Any) -> None:
        return None

    async def __aenter__(self) -> FakePlacesClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(
        self, _url: str, *, headers: dict[str, str], json: dict[str, Any]
    ) -> FakePlacesResponse:
        self.requests.append({"headers": headers, "json": json})
        return FakePlacesResponse(self.payloads.pop(0))


def _places(start: int, count: int) -> list[dict[str, Any]]:
    return [
        {
            "id": f"places/{index}",
            "displayName": {"text": f"Business {index}"},
            "formattedAddress": f"Address {index}",
            "location": {"latitude": 36.0 + index, "longitude": 7.0 + index},
            "nationalPhoneNumber": f"0550 00 00 {index:02d}",
            "rating": 4.0,
            "userRatingCount": 10,
        }
        for index in range(start, start + count)
    ]


def _target() -> SearchTarget:
    return SearchTarget(
        query="specialist doctors",
        location_text="Ain Beida, Oum El Bouaghi, Algeria",
        country_code="DZ",
        language="fr",
    )


@pytest.mark.asyncio
async def test_google_places_search_paginates_until_requested_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.discovery.google_places as google_places

    FakePlacesClient.payloads = [
        {"places": _places(1, 20), "nextPageToken": "page-2"},
        {"places": _places(21, 10)},
    ]
    FakePlacesClient.requests = []
    monkeypatch.setattr(google_places.httpx, "AsyncClient", FakePlacesClient)

    results = await GooglePlacesDiscoveryProvider(SecretStr("fake-key")).search(
        _target(), limit=25
    )

    assert len(results) == 25
    assert results[0].name == "Business 1"
    assert results[-1].name == "Business 25"
    assert len(FakePlacesClient.requests) == 2
    assert FakePlacesClient.requests[0]["json"]["pageSize"] == 20
    assert "pageToken" not in FakePlacesClient.requests[0]["json"]
    assert FakePlacesClient.requests[1]["json"]["pageSize"] == 5
    assert FakePlacesClient.requests[1]["json"]["pageToken"] == "page-2"


@pytest.mark.asyncio
async def test_google_places_search_returns_available_results_without_fabricating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.discovery.google_places as google_places

    FakePlacesClient.payloads = [{"places": _places(1, 8)}]
    FakePlacesClient.requests = []
    monkeypatch.setattr(google_places.httpx, "AsyncClient", FakePlacesClient)

    results = await GooglePlacesDiscoveryProvider(SecretStr("fake-key")).search(
        _target(), limit=25
    )

    assert len(results) == 8


def test_places_helper_generates_expected_count() -> None:
    assert len(_places(1, 25)) == 25
