from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx

from app.services.url_safety import validate_public_url


@dataclass(slots=True)
class PageObservations:
    url: str
    title: str | None = None
    links: list[str] = field(default_factory=list)
    booking_link_detected: bool = False
    whatsapp_link_detected: bool = False
    contact_form_detected: bool = False
    chat_widget_detected: bool = False


class _ObservationParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[str] = []
        self.has_form = False
        self.has_chat = False
        self._in_title = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value or "" for key, value in attrs}
        if tag.casefold() == "a" and values.get("href"):
            self.links.append(urljoin(self.base_url, values["href"]))
        elif tag.casefold() == "form":
            self.has_form = True
        elif tag.casefold() == "title":
            self._in_title = True
        blob = " ".join(values.values()).casefold()
        if re.search(r"intercom|drift|crisp|tawk|livechat|chat-widget", blob):
            self.has_chat = True

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data.strip())


def parse_observations(url: str, html: str) -> PageObservations:
    parser = _ObservationParser(url)
    parser.feed(html)
    lowered_links = [link.casefold() for link in parser.links]
    return PageObservations(
        url=url,
        title=" ".join(filter(None, parser.title_parts)) or None,
        links=parser.links,
        booking_link_detected=any(
            token in link
            for link in lowered_links
            for token in ("/book", "/appointment", "/reservation", "calendly")
        ),
        whatsapp_link_detected=any(
            "wa.me/" in link or "api.whatsapp.com" in link for link in lowered_links
        ),
        contact_form_detected=parser.has_form,
        chat_widget_detected=parser.has_chat,
    )


class SafeWebsiteCrawler:
    def __init__(self, *, timeout_seconds: float = 15, max_bytes: int = 2_000_000) -> None:
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes

    async def fetch(self, url: str) -> PageObservations:
        current = validate_public_url(url)
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as client:
            for _ in range(4):
                response = await client.get(
                    current,
                    headers={"User-Agent": "AI-Opportunity-Hunter/0.1 (+public-site-audit)"},
                )
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        response.raise_for_status()
                    current = validate_public_url(urljoin(current, location))
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type:
                    raise ValueError("Crawler only accepts HTML responses")
                if len(response.content) > self._max_bytes:
                    raise ValueError("HTML response exceeds configured size limit")
                return parse_observations(current, response.text)
        raise ValueError("Too many redirects")
