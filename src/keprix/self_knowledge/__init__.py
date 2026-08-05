"""Keprix self-knowledge: codebase introspection, RAG ingestion, and system-prompt layer."""

from .documents import KnowledgeDocument, generate_all_documents
from .ingestor import IngestResult, SelfKnowledgeIngestor

__all__ = [
    "generate_all_documents",
    "KnowledgeDocument",
    "SelfKnowledgeIngestor",
    "IngestResult",
]
