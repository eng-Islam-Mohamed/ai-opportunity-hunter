from __future__ import annotations

import httpx
from pydantic import SecretStr

from app.schemas.campaign import SearchTarget
from app.schemas.opportunity import DiscoveredBusiness

_MAX_TEXT_SEARCH_PAGE_SIZE = 20


class GooglePlacesDiscoveryProvider:
    def __init__(self, api_key: SecretStr, *, timeout_seconds: float = 20) -> None:
        self._api_key = api_key
        self._timeout = timeout_seconds

    async def search(self, target: SearchTarget, *, limit: int) -> list[DiscoveredBusiness]:
        if limit <= 0:
            return []

        headers = {
            "X-Goog-Api-Key": self._api_key.get_secret_value(),
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,places.location,"
                "places.websiteUri,places.nationalPhoneNumber,places.rating,places.userRatingCount,"
                "nextPageToken"
            ),
        }
        text_query = f"{target.query} in {target.location_text}"
        places: list[dict[str, object]] = []
        seen_place_ids: set[str] = set()
        page_token: str | None = None

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while len(places) < limit:
                remaining = limit - len(places)
                body: dict[str, object] = {
                    "textQuery": text_query,
                    "languageCode": target.language,
                    "pageSize": min(remaining, _MAX_TEXT_SEARCH_PAGE_SIZE),
                }
                if page_token:
                    body["pageToken"] = page_token

                response = await client.post(
                    "https://places.googleapis.com/v1/places:searchText", headers=headers, json=body
                )
                response.raise_for_status()
                payload = response.json()
                raw_places = payload.get("places", [])
                if not isinstance(raw_places, list):
                    break

                for raw_place in raw_places:
                    if not isinstance(raw_place, dict):
                        continue
                    place_id = raw_place.get("id")
                    if not isinstance(place_id, str) or place_id in seen_place_ids:
                        continue
                    seen_place_ids.add(place_id)
                    places.append(raw_place)
                    if len(places) >= limit:
                        break

                next_page_token = payload.get("nextPageToken")
                if not isinstance(next_page_token, str) or not next_page_token:
                    break
                if len(places) >= limit:
                    break
                page_token = next_page_token

        return [
            DiscoveredBusiness(
                provider="google_places",
                provider_entity_id=str(place["id"]),
                name=_place_display_name(place),
                address=_optional_string(place.get("formattedAddress")),
                country_code=target.country_code,
                latitude=_place_location_value(place, "latitude"),
                longitude=_place_location_value(place, "longitude"),
                website=_optional_string(place.get("websiteUri")),
                phone=_optional_string(place.get("nationalPhoneNumber")),
                rating=_optional_float(place.get("rating")),
                review_count=_optional_int(place.get("userRatingCount")),
            )
            for place in places[:limit]
        ]


def _place_display_name(place: dict[str, object]) -> str:
    display_name = place.get("displayName")
    if isinstance(display_name, dict):
        text = display_name.get("text")
        if isinstance(text, str) and text.strip():
            return text
    return "Unknown business"


def _place_location_value(place: dict[str, object], key: str) -> float | None:
    location = place.get("location")
    if not isinstance(location, dict):
        return None
    return _optional_float(location.get(key))


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _optional_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None
