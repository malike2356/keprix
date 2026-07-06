"""Search tool adapters (Prompt 56)."""

from __future__ import annotations

from typing import Any

from keprix.backend.tools.adapters.base import AdapterCitation, AdapterResult, ToolAdapter


class HttpSearchAdapter(ToolAdapter):
    supports_citations = True
    risk_level = "low"
    api_url: str = ""
    env_key: str = ""
    provider_label: str = ""

    def __init__(self, *, name: str, env_key: str, api_url: str, setup_doc: str) -> None:
        self.name = name
        self.category = "search"
        self.required_env = (env_key,)
        self.env_key = env_key
        self.api_url = api_url
        self.provider_label = name
        self.setup_doc = setup_doc

    async def execute(self, action: str, params: dict[str, Any]) -> AdapterResult:
        if action != "search":
            return AdapterResult(ok=False, error=f"Unsupported action: {action}")
        query = str(params.get("query") or "").strip()
        if not query:
            return AdapterResult(ok=False, error="query is required")

        if self.name == "tavily":
            return await self._run_tavily(query, params)
        if self.name == "exa":
            return await self._run_exa(query, params)
        if self.name == "brave":
            return await self._run_brave(query, params)
        return await self._run_generic(query, params)

    async def _run_tavily(self, query: str, params: dict[str, Any]) -> AdapterResult:
        from plugins.web.tavily.provider import _normalize_tavily_search_results, _tavily_request

        raw = _tavily_request("search", {"query": query, "max_results": int(params.get("limit", 5))})
        normalized = _normalize_tavily_search_results(raw)
        citations = [
            AdapterCitation(
                title=row.get("title", ""),
                url=row.get("url", ""),
                snippet=row.get("description", ""),
                source="tavily",
            )
            for row in normalized.get("data", {}).get("web", [])
        ]
        return AdapterResult(ok=True, data=normalized, citations=citations, cost_estimate_usd=0.01)

    async def _run_exa(self, query: str, params: dict[str, Any]) -> AdapterResult:
        import os

        import httpx

        response = httpx.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": os.environ["EXA_API_KEY"], "Content-Type": "application/json"},
            json={"query": query, "numResults": int(params.get("limit", 5))},
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        results = body.get("results", [])
        citations = [
            AdapterCitation(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("text", "")[:280],
                source="exa",
            )
            for item in results
        ]
        return AdapterResult(ok=True, data={"results": results}, citations=citations, cost_estimate_usd=0.02)

    async def _run_brave(self, query: str, params: dict[str, Any]) -> AdapterResult:
        import os

        import httpx

        response = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": os.environ["BRAVE_SEARCH_API_KEY"]},
            params={"q": query, "count": int(params.get("limit", 5))},
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        web = body.get("web", {}).get("results", [])
        citations = [
            AdapterCitation(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", ""),
                source="brave",
            )
            for item in web
        ]
        return AdapterResult(ok=True, data={"web": web}, citations=citations, cost_estimate_usd=0.01)

    async def _run_generic(self, query: str, params: dict[str, Any]) -> AdapterResult:
        import os

        import httpx

        response = httpx.post(
            self.api_url,
            json={"q": query, "query": query, "limit": int(params.get("limit", 5)), "api_key": os.environ[self.env_key]},
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        items = body.get("results") or body.get("organic") or []
        citations = [
            AdapterCitation(
                title=str(item.get("title") or ""),
                url=str(item.get("url") or item.get("link") or ""),
                snippet=str(item.get("snippet") or item.get("content") or "")[:280],
                source=self.provider_label,
            )
            for item in items
        ]
        return AdapterResult(ok=True, data=body, citations=citations, cost_estimate_usd=0.01)


SEARCH_ADAPTERS: list[ToolAdapter] = [
    HttpSearchAdapter(
        name="tavily",
        env_key="TAVILY_API_KEY",
        api_url="https://api.tavily.com/search",
        setup_doc="Get a key at https://app.tavily.com/home",
    ),
    HttpSearchAdapter(
        name="brave",
        env_key="BRAVE_SEARCH_API_KEY",
        api_url="https://api.search.brave.com/res/v1/web/search",
        setup_doc="Get a key at https://brave.com/search/api/",
    ),
    HttpSearchAdapter(
        name="serpapi",
        env_key="SERPAPI_API_KEY",
        api_url="https://serpapi.com/search.json",
        setup_doc="Get a key at https://serpapi.com/",
    ),
    HttpSearchAdapter(
        name="serper",
        env_key="SERPER_API_KEY",
        api_url="https://google.serper.dev/search",
        setup_doc="Get a key at https://serper.dev/",
    ),
    HttpSearchAdapter(
        name="serply",
        env_key="SERPLY_API_KEY",
        api_url="https://api.serply.io/v1/search/",
        setup_doc="Get a key at https://serply.io/",
    ),
    HttpSearchAdapter(
        name="exa",
        env_key="EXA_API_KEY",
        api_url="https://api.exa.ai/search",
        setup_doc="Get a key at https://exa.ai/",
    ),
    HttpSearchAdapter(
        name="linkup",
        env_key="LINKUP_API_KEY",
        api_url="https://api.linkup.so/v1/search",
        setup_doc="Get a key at https://www.linkup.so/",
    ),
]
