"""Registry of RAG source connectors."""

from __future__ import annotations

from typing import Any, Dict, List, Type

_CONNECTORS: Dict[str, Dict[str, Any]] = {}


def register_connector(
    connector_id: str,
    cls: Type[Any],
    *,
    description: str,
) -> None:
    _CONNECTORS[connector_id] = {"cls": cls, "description": description}


def get_connector(connector_id: str, **kwargs: Any) -> Any:
    entry = _CONNECTORS.get(connector_id)
    if not entry:
        raise KeyError(f"Unknown RAG connector: {connector_id!r}")
    return entry["cls"](**kwargs)


def list_connectors() -> List[Dict[str, str]]:
    return [
        {"id": connector_id, "description": meta["description"]}
        for connector_id, meta in sorted(_CONNECTORS.items())
    ]


def _register_builtin_connectors() -> None:
    from keprix.rag_pipeline.connectors.files import LocalFileSourceConnector, UrlSourceConnector
    from keprix.rag_pipeline.connectors.notion import NotionSourceConnector

    register_connector(
        "notion",
        NotionSourceConnector,
        description="Index Notion pages and databases for RAG search (read-only).",
    )
    register_connector(
        "local_file",
        LocalFileSourceConnector,
        description="Ingest a local filesystem path (or vault-relative path).",
    )
    register_connector(
        "url",
        UrlSourceConnector,
        description="Ingest an http(s) URL as plaintext or markdown.",
    )


_register_builtin_connectors()
