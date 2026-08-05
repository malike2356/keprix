"""Local keyword index for agent-sync knowledge."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from keprix.sync.github_bridge.config import GithubBridgeScope, github_bridge_index_path, resolve_github_bridge_scope


@dataclass
class IndexedChunk:
    path: str
    content: str
    tokens: list[str] = field(default_factory=list)
    product: str | None = None
    agent: str | None = None
    updated_at: str = ""


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9_./-]+", text.lower()) if len(token) > 1]


def load_index(scope: GithubBridgeScope | None = None) -> dict[str, Any]:
    resolved = resolve_github_bridge_scope(scope)
    path = github_bridge_index_path(resolved["scope_key"])
    if not path.is_file():
        return {"version": 1, "updated_at": "", "chunks": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "updated_at": "", "chunks": []}
    return {
        "version": raw.get("version") or 1,
        "updated_at": raw.get("updated_at") or raw.get("updatedAt") or "",
        "chunks": raw.get("chunks") or [],
    }


def save_index(chunks: list[IndexedChunk], scope: GithubBridgeScope | None = None) -> dict[str, Any]:
    resolved = resolve_github_bridge_scope(scope)
    payload = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "chunks": [asdict(chunk) for chunk in chunks],
    }
    path = github_bridge_index_path(resolved["scope_key"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def build_chunk(*, path: str, content: str, product: str | None = None, agent: str | None = None) -> IndexedChunk:
    clipped = content[:12_000]
    return IndexedChunk(
        path=path,
        content=clipped,
        tokens=_tokenize(f"{path}\n{clipped}"),
        product=product,
        agent=agent,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


def search_index(
    index: dict[str, Any],
    query: str,
    limit: int = 8,
    filters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    filters = filters or {}
    scored: list[dict[str, Any]] = []
    for chunk in index.get("chunks") or []:
        if filters.get("product") and chunk.get("product") and chunk.get("product") != filters["product"]:
            continue
        if filters.get("agent") and chunk.get("agent") and chunk.get("agent") != filters["agent"]:
            continue
        prefix = (filters.get("path_prefix") or "").lstrip("./")
        if prefix and not str(chunk.get("path") or "").startswith(prefix):
            continue
        tokens = chunk.get("tokens") or _tokenize(str(chunk.get("content") or ""))
        score = 0
        path = str(chunk.get("path") or "")
        content = str(chunk.get("content") or "")
        for token in q_tokens:
            if token in path.lower():
                score += 3
            if token in tokens:
                score += 1
        if score <= 0:
            continue
        needle = q_tokens[0]
        at = content.lower().find(needle)
        start = max(0, at - 40) if at >= 0 else 0
        snippet = re.sub(r"\s+", " ", content[start : start + 220]).strip() or content[:220]
        scored.append(
            {
                "path": path,
                "score": score,
                "snippet": snippet,
                "product": chunk.get("product"),
                "agent": chunk.get("agent"),
            }
        )
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[: max(1, min(limit, 50))]


def upsert_rag_chunks(chunks: list[IndexedChunk], scope: GithubBridgeScope | None = None) -> int:
    """Best-effort RAG upsert; keyword index remains the source of truth."""
    try:
        from keprix.memory.rag.self_knowledge import upsert_external_chunks  # type: ignore

        resolved = resolve_github_bridge_scope(scope)
        source = f"github-agent-sync:{resolved['scope_key']}"
        return int(
            upsert_external_chunks(
                source=source,
                chunks=[{"path": c.path, "content": c.content, "product": c.product, "agent": c.agent} for c in chunks[:120]],
            )
            or 0
        )
    except Exception:
        return 0
