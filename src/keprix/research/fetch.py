"""Fetch and extract readable text from web pages with SSRF protection."""

from __future__ import annotations

import ipaddress
import re
import socket
from html import unescape
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

MAX_FETCH_BYTES = 512_000
MAX_TEXT_CHARS = 16_000

_BLOCKED_HOSTS = {
    "localhost",
    "metadata.google.internal",
    "169.254.169.254",
}


def _normalize_url(url: str) -> str:
    return url.strip()


def _is_safe_url(url: str) -> bool:
    parsed = urlparse(_normalize_url(url))
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    if not host or host in _BLOCKED_HOSTS:
        return False
    try:
        addr = ipaddress.ip_address(host)
        return addr.is_global
    except ValueError:
        pass
    try:
        for info in socket.getaddrinfo(host, None):
            addr = ipaddress.ip_address(info[4][0])
            if not addr.is_global:
                return False
    except OSError:
        return False
    return True


async def fetch_page_text(url: str) -> tuple[str, str]:
    """Return (title, plain_text) for a URL. Raises ValueError on blocked/invalid URLs."""
    normalized = _normalize_url(url)
    if not _is_safe_url(normalized):
        raise ValueError(f"URL blocked by SSRF policy: {url}")

    async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
        response = await client.get(
            normalized,
            headers={"User-Agent": "Keprix-Research/1.0"},
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        raw = response.content[:MAX_FETCH_BYTES]
        if "html" not in content_type.lower() and not raw.lstrip().startswith(b"<"):
            text = raw.decode("utf-8", errors="replace").strip()
            return "", _truncate_text(text)

    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()
    title = unescape(soup.title.get_text(strip=True) if soup.title else "")
    text = unescape(soup.get_text(separator="\n", strip=True))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return title, _truncate_text(text)


def _truncate_text(text: str) -> str:
    if len(text) <= MAX_TEXT_CHARS:
        return text
    return text[:MAX_TEXT_CHARS] + "\n[truncated]"
