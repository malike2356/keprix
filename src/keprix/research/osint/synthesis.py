"""Cited OSINT report synthesis without unsupported claims."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def synthesize(entity: dict[str, Any], hits: list[dict[str, Any]], correlations: list[dict[str, Any]]) -> dict[str, Any]:
    claims = []
    uncited = 0
    source_errors = []
    for hit in hits:
        if hit.get("error"):
            source_errors.append({"source": hit.get("source"), "error": hit["error"]})
            continue
        url = str(hit.get("url") or hit.get("source_url") or "").strip()
        text = str(hit.get("claim") or hit.get("title") or "").strip()
        if url and text:
            claims.append({"text": text, "source_url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(), "confidence": hit.get("confidence", 0.5)})
        elif text:
            uncited += 1
    return {
        "entity": entity,
        "claims": claims,
        "correlations": correlations,
        "cited": uncited == 0,
        "uncited_claims_omitted": uncited,
        "source_errors": source_errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
