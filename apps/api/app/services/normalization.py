from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit


def normalize_name(name: str) -> str:
    value = re.sub(r"[^a-z0-9\s]", " ", name.casefold())
    return " ".join(value.split())


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    prefix = "+" if phone.strip().startswith("+") else ""
    digits = re.sub(r"\D", "", phone)
    return f"{prefix}{digits}" if len(digits) >= 7 else None


def canonicalize_url(url: str | None) -> str | None:
    if not url:
        return None
    candidate = url.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname.casefold().rstrip(".")
    port = f":{parsed.port}" if parsed.port and parsed.port not in {80, 443} else ""
    path = parsed.path.rstrip("/") or ""
    return urlunsplit((parsed.scheme.lower(), f"{host}{port}", path, parsed.query, ""))


def domain_from_url(url: str | None) -> str | None:
    canonical = canonicalize_url(url)
    if not canonical:
        return None
    host = urlsplit(canonical).hostname
    return host.removeprefix("www.") if host else None
