"""CLI helpers for Keprix self-knowledge RAG indexing."""

from __future__ import annotations

import asyncio
import json
from typing import Any


def cmd_memory_index_self(args: Any) -> int:
    from keprix.memory.rag.self_knowledge import SelfKnowledgeIndexer

    include_codebase = not bool(getattr(args, "docs_only", False))
    include_docs = not bool(getattr(args, "codebase_only", False))
    max_files = int(getattr(args, "max_files", 2000) or 2000)

    async def _run() -> dict[str, object]:
        stats = await SelfKnowledgeIndexer().index(
            include_codebase=include_codebase,
            include_docs=include_docs,
            include_capabilities=True,
            max_files=max_files,
        )
        return stats.to_dict()

    result = asyncio.run(_run())
    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


def cmd_memory_search_self(args: Any) -> int:
    from keprix.memory.rag.self_knowledge import retrieve_self_knowledge

    query = str(getattr(args, "query", "") or "").strip()
    if not query:
        print(json.dumps({"error": "query is required"}))
        return 1
    limit = int(getattr(args, "limit", 8) or 8)

    async def _run() -> list[dict[str, object]]:
        return await retrieve_self_knowledge(query, limit=limit, hybrid=True)

    results = asyncio.run(_run())
    print(json.dumps({"results": results}, indent=2))
    return 0
