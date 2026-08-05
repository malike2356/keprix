"""Built-in Graphiti-compatible store used when no external MCP URL is set."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix_constants import get_keprix_home


def local_store_root() -> Path:
    path = get_keprix_home() / "brain" / "graphiti" / "local"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", text or "")]


class LocalGraphitiStore:
    """Lightweight episodic store that speaks the bridge MCP tool contract."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or local_store_root()
        self.episodes_path = self.root / "episodes.jsonl"
        self.entities_path = self.root / "entities.json"

    def handle(self, tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        name = (tool or "").strip().lower()
        if name == "health":
            return {"ok": True, "backend": "builtin", "episodes": self._episode_count()}
        if name == "add_episode":
            return self.add_episode(
                name=str(args.get("name") or "episode"),
                content=str(args.get("episode_body") or args.get("content") or ""),
                source_ref=str(args.get("source") or args.get("source_ref") or ""),
            )
        if name in {"search", "query"}:
            return self.search(
                str(args.get("query") or ""),
                max_results=int(args.get("max_results") or 10),
                include_sources=bool(args.get("include_sources", True)),
            )
        if name == "get_entity":
            return self.get_entity(str(args.get("entity_id") or ""))
        raise RuntimeError(f"Unknown Graphiti tool: {tool}")

    def add_episode(self, *, name: str, content: str, source_ref: str) -> dict[str, Any]:
        episode_id = uuid4().hex[:12]
        tokens = _tokens(f"{name} {content}")
        entities = sorted(set(tokens))[:40]
        edges = []
        for left, right in zip(entities, entities[1:]):
            edges.append({"from": left, "to": right, "rel": "co_occurs"})
        episode = {
            "episode_id": episode_id,
            "name": name,
            "content": content,
            "source": source_ref,
            "entities": entities,
            "edges": edges,
            "created_at": _now(),
        }
        with self.episodes_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(episode) + "\n")
        self._merge_entities(entities, episode_id)
        return {
            "episode_id": episode_id,
            "id": episode_id,
            "nodes_added": len(entities),
            "edges_added": len(edges),
            "node_count": len(entities),
            "edge_count": len(edges),
        }

    def search(self, query: str, *, max_results: int = 10, include_sources: bool = True) -> dict[str, Any]:
        terms = set(_tokens(query))
        hits: list[dict[str, Any]] = []
        for episode in self._episodes():
            hay = f"{episode.get('name', '')} {episode.get('content', '')}".lower()
            score = sum(1 for term in terms if term in hay) if terms else 1
            if terms and score <= 0:
                continue
            hit: dict[str, Any] = {
                "fact": str(episode.get("content") or "")[:500],
                "score": score,
                "episode_id": episode.get("episode_id"),
                "name": episode.get("name"),
            }
            if include_sources:
                hit["source"] = episode.get("source")
            hits.append(hit)
        hits.sort(key=lambda item: int(item.get("score") or 0), reverse=True)
        return {"hits": hits[: max(1, max_results)], "results": hits[: max(1, max_results)]}

    def get_entity(self, entity_id: str) -> dict[str, Any]:
        entities = self._entities()
        key = entity_id.lower().strip()
        if key not in entities:
            return {"ok": False, "error": "entity not found", "entity_id": entity_id}
        return {"ok": True, "entity_id": key, **entities[key]}

    def _episode_count(self) -> int:
        return len(self._episodes())

    def _episodes(self) -> list[dict[str, Any]]:
        if not self.episodes_path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.episodes_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
        return rows

    def _entities(self) -> dict[str, Any]:
        if not self.entities_path.is_file():
            return {}
        try:
            payload = json.loads(self.entities_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _merge_entities(self, entities: list[str], episode_id: str) -> None:
        current = self._entities()
        for entity in entities:
            entry = current.get(entity) or {"entity_id": entity, "episode_ids": []}
            ids = list(entry.get("episode_ids") or [])
            if episode_id not in ids:
                ids.append(episode_id)
            entry["episode_ids"] = ids[-50:]
            entry["updated_at"] = _now()
            current[entity] = entry
        self.entities_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
