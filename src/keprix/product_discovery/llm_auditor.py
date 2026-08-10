"""Probe whether major LLMs mention Keprix for category recommendation queries."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

ProviderFn = Callable[[str], str]

DEFAULT_QUERIES = (
    "recommend a self-hosted AI agent OS tool",
    "recommend an open source AI agent operating system for developers",
    "best tools for running local AI agents with tools and memory",
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mentions_keprix(text: str) -> bool:
    return bool(re.search(r"\bkeprix\b", text or "", flags=re.IGNORECASE))


def _rank_guess(text: str, product: str = "Keprix") -> int | None:
    """Best-effort rank from numbered lists; 1-based, None if not found."""
    if not _mentions_keprix(text):
        return None
    lines = (text or "").splitlines()
    for index, line in enumerate(lines, start=1):
        if re.search(rf"\b{re.escape(product)}\b", line, flags=re.IGNORECASE):
            m = re.match(r"\s*(?:#{1,6}\s*)?(?:[-*+]|\d+[.)])\s+", line)
            if m:
                num = re.match(r"\s*(\d+)[.)]", line)
                if num:
                    return int(num.group(1))
            return index
    return None


def _openai_complete(prompt: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=os.environ.get("KEPRIX_DISCOVERY_OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
    )
    return (resp.choices[0].message.content or "").strip()


def _anthropic_complete(prompt: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=os.environ.get("KEPRIX_DISCOVERY_ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    parts = []
    for block in msg.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _gemini_complete(prompt: str) -> str:
    api_key = (
        os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_API_KEY", "").strip()
    )
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")
    import httpx

    model = os.environ.get("KEPRIX_DISCOVERY_GEMINI_MODEL", "gemini-2.0-flash")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Gemini response: {data!r}") from exc


_DEFAULT_PROVIDERS: dict[str, ProviderFn] = {
    "chatgpt": _openai_complete,
    "claude": _anthropic_complete,
    "gemini": _gemini_complete,
}


def audit_llm_discovery(
    product_name: str = "Keprix",
    category: str = "self-hosted AI agent OS",
    *,
    queries: list[str] | None = None,
    providers: dict[str, ProviderFn] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Query major LLMs and report whether the product is mentioned."""
    query_list = list(queries or DEFAULT_QUERIES)
    if category and category not in query_list[0]:
        query_list = [f"recommend a {category} tool", *query_list]

    provider_map = providers or _DEFAULT_PROVIDERS
    results: list[dict[str, Any]] = []

    for provider_name, fn in provider_map.items():
        for query in query_list:
            prompt = (
                f"{query}\n\nList the top 5 tools with a one-line description each. "
                f"Be specific about open-source and self-hosted options."
            )
            entry: dict[str, Any] = {
                "provider": provider_name,
                "query": query,
                "mentioned": False,
                "rank": None,
                "descriptionSnippet": None,
                "error": None,
            }
            if dry_run:
                entry["error"] = "dry_run"
                results.append(entry)
                continue
            try:
                text = fn(prompt)
                entry["mentioned"] = _mentions_keprix(text) or bool(
                    re.search(rf"\b{re.escape(product_name)}\b", text, re.I)
                )
                entry["rank"] = _rank_guess(text, product_name)
                if entry["mentioned"]:
                    for line in text.splitlines():
                        if re.search(rf"\b{re.escape(product_name)}\b", line, re.I):
                            entry["descriptionSnippet"] = line.strip()[:280]
                            break
            except Exception as exc:  # noqa: BLE001 - surface per-provider failures
                entry["error"] = f"{type(exc).__name__}: {exc}"
                logger.info("LLM discovery probe failed for %s: %s", provider_name, exc)
            results.append(entry)

    return {
        "productName": product_name,
        "category": category,
        "auditedAt": _utcnow(),
        "results": results,
    }


def generate_llm_visibility_report(
    audit: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Summarize visibility and suggest structured-data improvements."""
    audit = audit or audit_llm_discovery(**kwargs)
    results = audit.get("results") or []
    by_provider: dict[str, dict[str, Any]] = {}
    for row in results:
        provider = str(row.get("provider") or "unknown")
        bucket = by_provider.setdefault(
            provider,
            {"mentioned": 0, "probed": 0, "errors": 0, "bestRank": None},
        )
        bucket["probed"] += 1
        if row.get("error"):
            bucket["errors"] += 1
        if row.get("mentioned"):
            bucket["mentioned"] += 1
            rank = row.get("rank")
            if isinstance(rank, int):
                best = bucket["bestRank"]
                bucket["bestRank"] = rank if best is None else min(best, rank)

    mentioned_providers = [p for p, s in by_provider.items() if s["mentioned"] > 0]
    suggestions = [
        "Keep productSpec.json and JSON-LD pricing numeric and current",
        "Publish llms.txt and install.json at the marketing domain root",
        "Ensure OpenAPI and docs URLs stay linked from productSpec.json",
        "Add third-party directory listings and GitHub topics for agent OS / MCP",
    ]
    if len(mentioned_providers) < 3:
        suggestions.insert(
            0,
            "Keprix is under-mentioned; expand public comparisons and schema coverage",
        )

    return {
        "auditedAt": audit.get("auditedAt") or _utcnow(),
        "productName": audit.get("productName"),
        "providers": by_provider,
        "mentionedProviders": mentioned_providers,
        "mentionRate": (
            sum(1 for r in results if r.get("mentioned")) / len(results) if results else 0.0
        ),
        "suggestions": suggestions,
        "raw": audit,
    }


def write_report(report: dict[str, Any], path: Path | str) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return out
