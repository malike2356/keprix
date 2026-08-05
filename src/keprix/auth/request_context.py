"""Helpers for recording coarse authentication request metadata."""

from __future__ import annotations

from fastapi import Request


def client_ip(request: Request) -> str:
    """Return the direct client address, preferring the first forwarded address."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else ""


def client_label(request: Request) -> str:
    """Return a short, non-sensitive label for the current browser or client.

    Prefers an explicit `X-Client-Label` header (sent by the frontend with
    `navigator.userAgent`) so callers can supply a friendly label directly.
    Falls back to a coarse browser/OS summary parsed from the User-Agent
    header when no label is supplied.
    """
    custom = request.headers.get("x-client-label", "").strip()
    if custom:
        return custom[:160]
    user_agent = request.headers.get("user-agent", "").strip()
    if not user_agent:
        return "Unknown device"
    return _coarse_device_from_user_agent(user_agent)


def _coarse_device_from_user_agent(user_agent: str) -> str:
    ua = user_agent.strip()
    if not ua:
        return "Unknown device"
    lowered = ua.lower()
    browser = "Browser"
    if "edg/" in lowered or "edge/" in lowered:
        browser = "Edge"
    elif "chrome/" in lowered and "chromium" not in lowered:
        browser = "Chrome"
    elif "firefox/" in lowered:
        browser = "Firefox"
    elif "safari/" in lowered and "chrome/" not in lowered:
        browser = "Safari"
    platform = "Unknown OS"
    if "windows" in lowered:
        platform = "Windows"
    elif "mac os" in lowered or "macintosh" in lowered:
        platform = "macOS"
    elif "android" in lowered:
        platform = "Android"
    elif "iphone" in lowered or "ipad" in lowered:
        platform = "iOS"
    elif "linux" in lowered:
        platform = "Linux"
    return f"{browser} on {platform}"
