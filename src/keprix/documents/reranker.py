"""Lightweight reranker for retrieved chunks."""

from __future__ import annotations

import re
from typing import Any


def rerank_chunks(query: str, chunks: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    terms = [term for term in re.findall(r"\w+", query.lower()) if len(term) > 2]
    ranked: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        content = str(chunk.get("content") or "").lower()
        overlap = sum(1 for term in terms if term in content)
        boost = overlap / max(len(terms), 1)
        score = float(chunk.get("score") or 0.0) + (boost * 0.2)
        ranked.append((score, {**chunk, "rerank_score": score}))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:limit]]
