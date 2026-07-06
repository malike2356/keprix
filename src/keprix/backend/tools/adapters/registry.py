"""Tool adapter registry (Prompt 56)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from keprix.backend.tools.adapters.automation import AUTOMATION_ADAPTERS
from keprix.backend.tools.adapters.base import AdapterResult, ToolAdapter
from keprix.backend.tools.adapters.code_search import CODE_SEARCH_ADAPTERS
from keprix.backend.tools.adapters.databases import DATABASE_ADAPTERS
from keprix.backend.tools.adapters.evaluation import EVALUATION_ADAPTERS
from keprix.backend.tools.adapters.media import MEDIA_ADAPTERS
from keprix.backend.tools.adapters.rag_documents import RAG_DOCUMENT_ADAPTERS
from keprix.backend.tools.adapters.sandboxes import SANDBOX_ADAPTERS
from keprix.backend.tools.adapters.scraping import SCRAPING_ADAPTERS
from keprix.backend.tools.adapters.search import SEARCH_ADAPTERS
from keprix.backend.tools.adapters.vector_stores import VECTOR_STORE_ADAPTERS

ALL_ADAPTERS: list[ToolAdapter] = [
    *SEARCH_ADAPTERS,
    *SCRAPING_ADAPTERS,
    *RAG_DOCUMENT_ADAPTERS,
    *DATABASE_ADAPTERS,
    *VECTOR_STORE_ADAPTERS,
    *MEDIA_ADAPTERS,
    *CODE_SEARCH_ADAPTERS,
    *AUTOMATION_ADAPTERS,
    *SANDBOX_ADAPTERS,
    *EVALUATION_ADAPTERS,
]

_ADAPTER_INDEX: dict[str, ToolAdapter] = {adapter.name: adapter for adapter in ALL_ADAPTERS}


def list_adapters(*, category: str | None = None) -> list[dict[str, Any]]:
    rows = ALL_ADAPTERS
    if category:
        rows = [adapter for adapter in rows if adapter.category == category]
    return [adapter.metadata() for adapter in rows]


def list_categories() -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for adapter in ALL_ADAPTERS:
        counts[adapter.category] += 1
    return dict(sorted(counts.items()))


def get_adapter(name: str) -> ToolAdapter | None:
    return _ADAPTER_INDEX.get(name)


async def run_adapter(
    name: str,
    action: str,
    params: dict[str, Any],
    *,
    dry_run: bool = True,
    approved: bool = False,
) -> AdapterResult:
    adapter = get_adapter(name)
    if adapter is None:
        return AdapterResult(ok=False, error=f"Unknown adapter: {name}")
    return await adapter.run(action, params, dry_run=dry_run, approved=approved)
