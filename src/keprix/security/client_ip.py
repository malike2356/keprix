"""Resolve client IP with optional trusted-proxy forwarding."""

from __future__ import annotations

import ipaddress
import os
from typing import Iterable

from starlette.requests import Request


def trusted_proxy_cidrs() -> list[str]:
    raw = os.getenv("KEPRIX_TRUSTED_PROXIES", "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def trust_all_proxies() -> bool:
    return "*" in trusted_proxy_cidrs() or "fly=any" in trusted_proxy_cidrs()


def _peer_ip(request: Request) -> str | None:
    if request.client and request.client.host:
        return request.client.host
    return None


def _ip_in_cidrs(ip: str, cidrs: Iterable[str]) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for cidr in cidrs:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            if cidr == ip:
                return True
            continue
        if addr in network:
            return True
    return False


def client_ip(request: Request, *, default: str = "unknown") -> str:
    """Return the client IP.

    When ``KEPRIX_TRUSTED_PROXIES`` is set, honor ``X-Forwarded-For`` /
    ``Forwarded`` only if the immediate peer is in that allow-list.
    When unset, ignore forwarded headers (fail closed against spoofing).
    """
    peer = _peer_ip(request)
    cidrs = trusted_proxy_cidrs()
    allow_forwarded = bool(peer and cidrs and (trust_all_proxies() or _ip_in_cidrs(peer, [c for c in cidrs if c not in {"*", "fly=any"}])))
    if peer and allow_forwarded:
        forwarded = (
            request.headers.get("x-forwarded-for")
            or request.headers.get("X-Forwarded-For")
            or ""
        ).strip()
        if forwarded:
            return forwarded.split(",")[0].strip() or peer
        # RFC 7239 Forwarded: for=1.2.3.4
        fwd = request.headers.get("forwarded") or request.headers.get("Forwarded") or ""
        for part in fwd.split(";"):
            part = part.strip()
            if part.lower().startswith("for="):
                value = part.split("=", 1)[1].strip().strip('"')
                if value.startswith("["):
                    value = value.strip("[]")
                if ":" in value and value.count(":") == 1 and not value.startswith("["):
                    # host:port
                    value = value.rsplit(":", 1)[0]
                return value or peer
        return peer
    return peer or default


def is_https_request(request: Request) -> bool:
    """True when the request is HTTPS, including via trusted proxy proto."""
    if request.url.scheme == "https":
        return True
    peer = _peer_ip(request)
    cidrs = trusted_proxy_cidrs()
    allow = bool(peer and cidrs and (trust_all_proxies() or _ip_in_cidrs(peer, [c for c in cidrs if c not in {"*", "fly=any"}])))
    if allow:
        proto = (
            request.headers.get("x-forwarded-proto")
            or request.headers.get("X-Forwarded-Proto")
            or ""
        ).split(",")[0].strip().lower()
        return proto == "https"
    return False
