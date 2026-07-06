"""Vector store adapters (Prompt 56)."""

from __future__ import annotations

from typing import Any

from keprix.backend.tools.adapters.base import AdapterResult, ToolAdapter


class VectorStoreAdapter(ToolAdapter):
    category = "vector_stores"
    risk_level = "medium"
    requires_approval_for_write = True

    def __init__(self, *, name: str, env_key: str) -> None:
        self.name = name
        self.required_env = (env_key,)
        self.setup_doc = f"Configure {env_key} for read-only vector search."

    async def execute(self, action: str, params: dict[str, Any]) -> AdapterResult:
        if action != "search":
            return AdapterResult(ok=False, error=f"Unsupported action: {action}")
        query = str(params.get("query") or "")
        collection = str(params.get("collection") or "default")
        return AdapterResult(
            ok=True,
            data={"query": query, "collection": collection, "matches": [], "store": self.name},
        )


VECTOR_STORE_ADAPTERS: list[ToolAdapter] = [
    VectorStoreAdapter(name="qdrant", env_key="QDRANT_URL"),
    VectorStoreAdapter(name="weaviate", env_key="WEAVIATE_URL"),
    VectorStoreAdapter(name="mongodb_vector", env_key="MONGODB_VECTOR_URI"),
]
