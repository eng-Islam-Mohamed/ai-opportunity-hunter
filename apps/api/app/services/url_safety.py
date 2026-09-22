from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeUrlError(ValueError):
    pass


def validate_public_url(url: str, *, resolve_dns: bool = True) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeUrlError("Only absolute HTTP(S) URLs are allowed")
    hostname = parsed.hostname.casefold().rstrip(".")
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        raise UnsafeUrlError("Local destinations are blocked")
    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        if not resolve_dns:
            return url
        try:
            addresses = list(
                {
                    ipaddress.ip_address(item[4][0])
                    for item in socket.getaddrinfo(
                        hostname, parsed.port or 443, type=socket.SOCK_STREAM
                    )
                }
            )
        except socket.gaierror as exc:
            raise UnsafeUrlError("Destination DNS could not be resolved") from exc
    for address in addresses:
        if not address.is_global:
            raise UnsafeUrlError(
                "Private, loopback, reserved, or link-local destinations are blocked"
            )
    return url
