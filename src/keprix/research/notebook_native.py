"""Native Quick Notebook source synthesis."""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from keprix.research.notebook_job_store import NotebookSource

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9-]{2,}", re.IGNORECASE)


def normalize_notebook_source(data: dict[str, Any]) -> NotebookSource:
    kind = str(data.get("kind") or "text").strip().lower()
    if kind not in {"text", "url", "file", "session_export"}:
        kind = "text"
    ref = str(data.get("ref") or data.get("content") or "").strip()
    title = str(data.get("title") or "").strip()
    if not title:
        if kind == "url":
            title = ref[:80] or "URL source"
        elif kind == "file":
            title = "Uploaded file"
        elif kind == "session_export":
            title = "Session export"
        else:
            title = "Pasted source"
    excerpt = str(data.get("excerpt") or ref).strip()
    return NotebookSource(
        id=str(data.get("id") or f"S{uuid4().hex[:6]}"),
        kind=kind,  # type: ignore[arg-type]
        ref=ref,
        title=title[:160],
        excerpt=_clean_excerpt(excerpt),
    )


def _clean_excerpt(value: str, limit: int = 4000) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    return compact[:limit]


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", _clean_excerpt(text, 6000))
    return [part.strip() for part in parts if len(part.strip()) >= 24]


def _query_terms(query: str) -> set[str]:
    return {word.lower() for word in _WORD_RE.findall(query)}


def _best_sentence(query: str, source: NotebookSource) -> str:
    terms = _query_terms(query)
    candidates = _sentences(source.excerpt or source.ref) or [_clean_excerpt(source.excerpt or source.ref, 500)]
    if not terms:
        return candidates[0]
    return max(
        candidates,
        key=lambda sentence: sum(1 for word in _WORD_RE.findall(sentence.lower()) if word in terms),
    )


class NotebookNativeEngine:
    """Deterministic, source-grounded report builder for Quick Notebook."""

    def __init__(self, max_sources: int = 20) -> None:
        self.max_sources = max_sources

    def run(self, *, query: str, sources: list[NotebookSource]) -> dict[str, Any]:
        selected = [source for source in sources if (source.excerpt or source.ref).strip()][: self.max_sources]
        if len(selected) < 2:
            raise ValueError("Quick Notebook requires at least two sources")

        citations: list[dict[str, Any]] = []
        findings: list[str] = []
        for index, source in enumerate(selected, start=1):
            marker = f"S{index}"
            sentence = _best_sentence(query, source)
            citations.append(
                {
                    "id": marker,
                    "source_id": source.id,
                    "title": source.title,
                    "kind": source.kind,
                    "ref": source.ref,
                    "excerpt": sentence,
                }
            )
            findings.append(f"- {sentence} [{marker}]")

        synthesis = self._synthesis_sentence(query, citations)
        report = "\n\n".join(
            [
                "# Notebook Research Report",
                f"**Query:** {query}",
                "## Answer",
                synthesis,
                "## Source-grounded findings",
                "\n".join(findings),
                "## Citations",
                "\n".join(
                    f"- [{citation['id']}] {citation['title']} ({citation['kind']}: {citation['ref'][:160]})"
                    for citation in citations
                ),
            ]
        )
        return {"report_md": report + "\n", "citations": citations}

    def _synthesis_sentence(self, query: str, citations: list[dict[str, Any]]) -> str:
        first = citations[0]["excerpt"].rstrip(".")
        second = citations[1]["excerpt"].rstrip(".")
        return (
            f"For `{query}`, the notebook sources point to two anchored observations: "
            f"{first} [S1]. The second source adds that {second} [S2]."
        )
