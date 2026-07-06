"""Scraping safety policy (Prompt 56)."""

from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import urlparse


BLOCKED_HOST_PATTERNS = (
    re.compile(r"login", re.I),
    re.compile(r"accounts\.", re.I),
    re.compile(r"auth\.", re.I),
)

PRIVATE_ACCOUNT_HINTS = (
    "private account",
    "sign in to continue",
    "members only",
)


@dataclass
class ScrapingDecision:
    allowed: bool
    reason: str = ""


class ScrapingSafetyPolicy:
    """Domain rate limits and basic safety checks for scraping adapters."""

    def __init__(self, *, max_requests_per_minute: int = 6) -> None:
        self._max_requests = max_requests_per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)

    def evaluate(self, url: str, *, content_hint: str = "") -> ScrapingDecision:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return ScrapingDecision(False, "Only http(s) URLs are allowed")
        host = (parsed.hostname or "").lower()
        if not host:
            return ScrapingDecision(False, "Missing hostname")
        for pattern in BLOCKED_HOST_PATTERNS:
            if pattern.search(host):
                return ScrapingDecision(False, "Login or auth endpoints are blocked")
        lowered = content_hint.lower()
        if any(hint in lowered for hint in PRIVATE_ACCOUNT_HINTS):
            return ScrapingDecision(False, "Private account scraping is blocked")
        if not self._within_rate_limit(host):
            return ScrapingDecision(False, f"Rate limit exceeded for {host}")
        return ScrapingDecision(True)

    def _within_rate_limit(self, host: str) -> bool:
        now = time.time()
        window_start = now - 60
        hits = [stamp for stamp in self._hits[host] if stamp >= window_start]
        if len(hits) >= self._max_requests:
            self._hits[host] = hits
            return False
        hits.append(now)
        self._hits[host] = hits
        return True
