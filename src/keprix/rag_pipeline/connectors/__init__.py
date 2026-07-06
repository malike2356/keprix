"""External source connectors for RAG pipeline ingestion."""

from __future__ import annotations

from typing import Any, Dict, List, Protocol


class SourceConnector(Protocol):
    connector_id: str

    def list_documents(self) -> List[Dict[str, Any]]:
        """Return document descriptors: {id, title, metadata}."""

    def fetch_document(self, doc_id: str) -> Dict[str, Any]:
        """Return {id, title, content, metadata} with plain text or markdown content."""
