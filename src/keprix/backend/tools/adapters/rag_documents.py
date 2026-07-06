"""Document and RAG adapters (Prompt 56)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.backend.tools.adapters.base import AdapterResult, ToolAdapter


class DocumentAdapter(ToolAdapter):
    category = "documents"
    risk_level = "low"
    supports_dry_run = True
    file_suffix: str = ""

    def __init__(self, *, name: str, suffix: str) -> None:
        self.name = name
        self.file_suffix = suffix
        self.required_env = ()
        self.setup_doc = f"Reads local {suffix} files from workspace paths."

    async def execute(self, action: str, params: dict[str, Any]) -> AdapterResult:
        if action not in {"read", "parse"}:
            return AdapterResult(ok=False, error=f"Unsupported action: {action}")
        path = Path(str(params.get("path") or ""))
        if not path.exists():
            return AdapterResult(ok=False, error=f"File not found: {path}")
        if path.suffix.lower() not in {self.file_suffix, self.file_suffix.lstrip(".")}:
            return AdapterResult(ok=False, error=f"Expected {self.file_suffix} file")
        text = path.read_text(encoding="utf-8", errors="replace")
        return AdapterResult(ok=True, data={"path": str(path), "text": text, "format": self.name})


class WebsiteSearchAdapter(ToolAdapter):
    name = "website_search"
    category = "documents"
    risk_level = "low"
    required_env = ("TAVILY_API_KEY",)
    supports_citations = True
    setup_doc = "Uses Tavily search scoped to a domain."

    async def execute(self, action: str, params: dict[str, Any]) -> AdapterResult:
        from keprix.backend.tools.adapters.search import SEARCH_ADAPTERS

        tavily = next(item for item in SEARCH_ADAPTERS if item.name == "tavily")
        query = str(params.get("query") or "")
        domain = str(params.get("domain") or "")
        scoped = f"site:{domain} {query}".strip()
        return await tavily.execute("search", {"query": scoped, "limit": params.get("limit", 5)})


RAG_DOCUMENT_ADAPTERS: list[ToolAdapter] = [
    DocumentAdapter(name="pdf", suffix=".pdf"),
    DocumentAdapter(name="docx", suffix=".docx"),
    DocumentAdapter(name="txt", suffix=".txt"),
    DocumentAdapter(name="csv", suffix=".csv"),
    DocumentAdapter(name="json", suffix=".json"),
    DocumentAdapter(name="xml", suffix=".xml"),
    DocumentAdapter(name="mdx", suffix=".mdx"),
    WebsiteSearchAdapter(),
]
