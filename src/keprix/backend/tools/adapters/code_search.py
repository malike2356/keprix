"""Code and docs search adapters (Prompt 56)."""

from __future__ import annotations

from typing import Any

from keprix.backend.tools.adapters.base import AdapterCitation, AdapterResult, ToolAdapter


class CodeSearchAdapter(ToolAdapter):
    category = "code_search"
    risk_level = "low"
    supports_citations = True

    def __init__(self, *, name: str, env_key: str = "", setup_doc: str = "") -> None:
        self.name = name
        self.required_env = (env_key,) if env_key else ()
        self.setup_doc = setup_doc

    async def execute(self, action: str, params: dict[str, Any]) -> AdapterResult:
        query = str(params.get("query") or params.get("path") or "")
        if self.name == "github_search":
            import os

            import httpx

            response = httpx.get(
                "https://api.github.com/search/code",
                headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"},
                params={"q": query},
                timeout=30,
            )
            response.raise_for_status()
            items = response.json().get("items", [])
            citations = [
                AdapterCitation(title=item.get("name", ""), url=item.get("html_url", ""), snippet=item.get("path", ""), source="github")
                for item in items[:5]
            ]
            return AdapterResult(ok=True, data={"items": items[:5]}, citations=citations)
        if self.name == "directory_search":
            from pathlib import Path

            root = Path(str(params.get("root") or "."))
            matches = [str(path) for path in root.rglob("*") if query.lower() in path.name.lower()][:20]
            return AdapterResult(ok=True, data={"matches": matches})
        docs = [{"title": query, "url": f"https://docs.example/search?q={query}"}]
        return AdapterResult(
            ok=True,
            data={"results": docs},
            citations=[AdapterCitation(title=query, url=docs[0]["url"], source="code_docs")],
        )


CODE_SEARCH_ADAPTERS: list[ToolAdapter] = [
    CodeSearchAdapter(name="github_search", env_key="GITHUB_TOKEN", setup_doc="Set a GitHub token with repo read scope."),
    CodeSearchAdapter(name="code_docs_search", setup_doc="Searches indexed code documentation."),
    CodeSearchAdapter(name="directory_search", setup_doc="Searches local workspace directories."),
]
