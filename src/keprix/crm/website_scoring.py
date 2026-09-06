"""Explainable website quality and search-rank checks for CRM enrichment."""

from __future__ import annotations

import re
import json
import os
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.meta_description = ""
        self.text: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): (value or "") for key, value in attrs}
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() == "meta" and values.get("name", "").lower() == "description":
            self.meta_description = values.get("content", "").strip()

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        self.text.append(data)


def score_website(url: str, *, fetcher: Callable[[str], tuple[int, dict[str, str], bytes]] | None = None) -> dict[str, Any]:
    """Score six observable checks without treating a failed fetch as an exception."""
    normalized = str(url or "").strip()
    parsed = urlparse(normalized)
    checks: list[dict[str, Any]] = []
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {"score": 1, "weakness": "invalid website URL", "checks": [{"id": "reachable", "passed": False}]}
    checks.append({"id": "https", "passed": parsed.scheme == "https", "label": "HTTPS"})
    try:
        status, headers, content = (fetcher or _fetch)(normalized)
    except Exception as exc:  # noqa: BLE001
        checks.append({"id": "reachable", "passed": False, "detail": str(exc)})
        return {"score": 1, "weakness": "website did not respond", "checks": checks}
    parser = _PageParser()
    parser.feed(content.decode("utf-8", errors="replace"))
    html = content.decode("utf-8", errors="replace").lower()
    checks.extend(
        [
            {"id": "reachable", "passed": 200 <= status < 400, "status": status},
            {"id": "mobile_viewport", "passed": 'name="viewport"' in html and "width=device-width" in html},
            {"id": "title_meta", "passed": bool(parser.title.strip() and parser.meta_description.strip())},
            {"id": "load_weight", "passed": len(content) <= 5 * 1024 * 1024, "bytes": len(content)},
            {"id": "contact_presence", "passed": bool(re.search(r"mailto:|tel:|\bcontact\b|@", html))},
        ]
    )
    passed = sum(1 for check in checks if check.get("passed"))
    score = max(1, min(10, round(1 + 9 * passed / len(checks))))
    weaknesses = {
        "https": "no HTTPS",
        "reachable": "website unavailable",
        "mobile_viewport": "no responsive viewport",
        "title_meta": "missing title or meta description",
        "load_weight": "page is too heavy",
        "contact_presence": "no visible contact information",
    }
    weakness = next((weaknesses[str(check["id"])] for check in checks if not check.get("passed")), "none detected")
    return {"score": score, "weakness": weakness, "checks": checks, "url": normalized}


def _fetch(url: str) -> tuple[int, dict[str, str], bytes]:
    request = Request(url, headers={"User-Agent": "Keprix-Website-Scorer/1.0"})
    with urlopen(request, timeout=15) as response:
        return int(response.status), dict(response.headers), response.read(5 * 1024 * 1024 + 1)


def check_rank(domain: str, keyword: str, *, searcher: Callable[[str], list[dict[str, Any]]] | None = None) -> dict[str, Any]:
    """Return a truthful top-three result from normalized search results."""
    domain = str(domain or "").strip().lower().removeprefix("www.")
    if not domain or not str(keyword or "").strip():
        return {"ranks_top3": False, "position": None, "error": "domain_and_keyword_required"}
    try:
        results = (searcher or _search)(str(keyword))
    except Exception as exc:  # noqa: BLE001
        return {"ranks_top3": False, "position": None, "error": str(exc)}
    for position, result in enumerate(results, 1):
        host = urlparse(str(result.get("url") or "")).netloc.lower().removeprefix("www.")
        if host == domain or host.endswith("." + domain):
            return {"ranks_top3": position <= 3, "position": position}
    return {"ranks_top3": False, "position": None}


def _search(_keyword: str) -> list[dict[str, Any]]:
    key = os.environ.get("SERPAPI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("SERPAPI_API_KEY is not configured")
    query = urlencode({"q": _keyword, "api_key": key, "engine": "google", "num": 10})
    request = Request("https://serpapi.com/search.json?" + query, headers={"User-Agent": "Keprix-Website-Scorer/1.0"})
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return list(payload.get("organic_results") or [])
