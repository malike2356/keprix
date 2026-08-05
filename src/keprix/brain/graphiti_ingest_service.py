"""Graphiti ingest jobs for sessions, research reports, vault files, and manual text."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keprix.brain.graphiti_bridge import GraphitiBridge, graphiti_enabled
from keprix.brain.graphiti_job_store import GraphitiIngestJob, GraphitiJobStore
from keprix.security.ingest_poison_gate import evaluate_ingest_text


class GraphitiIngestService:
    def __init__(self, *, bridge: GraphitiBridge | None = None, store: GraphitiJobStore | None = None) -> None:
        self.bridge = bridge or GraphitiBridge()
        self.store = store or GraphitiJobStore()

    def ingest(self, *, source_type: str, source_ref: str, content: str | None = None) -> GraphitiIngestJob:
        job = self.store.save(GraphitiIngestJob(source_type=source_type, source_ref=source_ref, status="running"))
        try:
            if not graphiti_enabled():
                raise RuntimeError("Graphiti bridge is disabled")
            text = content if content is not None else self._load_content(source_type, source_ref)
            verdict = evaluate_ingest_text(text, source_type=source_type, source_ref=source_ref)
            if verdict.rejected:
                raise RuntimeError(f"Graphiti ingest rejected: {', '.join(verdict.reasons) or 'policy'}")
            result = self.bridge.add_episode(name=f"{source_type}:{source_ref}", content=text, source_ref=source_ref)
            job.status = "done"
            job.graphiti_episode_id = str(result.get("episode_id") or result.get("id") or "")
            job.nodes_added = int(result.get("nodes_added") or result.get("node_count") or result.get("nodes") or 0)
            job.edges_added = int(result.get("edges_added") or result.get("edge_count") or result.get("edges") or 0)
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
        return self.store.save(job)

    def query(self, query: str, *, max_results: int = 10, include_sources: bool = True) -> dict[str, Any]:
        if not graphiti_enabled():
            return {"ok": False, "error": "Graphiti bridge is disabled", "fallback": "native brain search"}
        try:
            result = self.bridge.query(query, max_results=max_results, include_sources=include_sources)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "fallback": "native brain search"}
        hits = result.get("hits") or result.get("results") or []
        return {"ok": True, "hits": hits, "raw": result}

    def _load_content(self, source_type: str, source_ref: str) -> str:
        if source_type in {"research", "manual"}:
            path = Path(source_ref).expanduser()
            if path.is_file():
                return path.read_text(encoding="utf-8")
            return source_ref
        if source_type == "vault_file":
            from keprix.vault.config import get_configured_provider

            import asyncio

            return asyncio.run(get_configured_provider().read_file(source_ref))
        if source_type == "session":
            path = Path(source_ref).expanduser()
            if path.is_file():
                data = json.loads(path.read_text(encoding="utf-8"))
                messages = data.get("messages") or data.get("turns") or []
                return "\n".join(str(item.get("content") or item) for item in messages)
        path = Path(source_ref).expanduser()
        if path.is_file():
            return path.read_text(encoding="utf-8")
        return source_ref
