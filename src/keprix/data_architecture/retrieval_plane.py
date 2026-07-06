"""Retrieval plane facade over memory and RAG modules."""

from __future__ import annotations

from typing import Any

from keprix.data_architecture.graph_edges import add_graph_edge, list_graph_edges


async def retrieval_status() -> dict[str, Any]:
    engine = "pgvector"
    try:
        from keprix.database import get_session_factory

        if get_session_factory() is None:
            engine = "local"
    except Exception:
        engine = "local"
    return {
        "engine": engine,
        "supports_graph_edges": True,
        "separates_sources_and_summaries": True,
        "graph_storage": "postgres" if engine == "pgvector" else "sqlite",
    }


__all__ = ["retrieval_status", "add_graph_edge", "list_graph_edges"]
