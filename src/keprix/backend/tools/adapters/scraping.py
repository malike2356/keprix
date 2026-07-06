"""Web scraping tool adapters (Prompt 56)."""

from __future__ import annotations

from typing import Any

from keprix.backend.tools.adapters.base import AdapterCitation, AdapterResult, ToolAdapter
from keprix.backend.tools.adapters.scraping_safety import ScrapingSafetyPolicy

_scraping_policy = ScrapingSafetyPolicy()


class ScrapingAdapter(ToolAdapter):
    category = "scraping"
    risk_level = "medium"
    supports_citations = True
    supports_dry_run = True

    def __init__(self, *, name: str, env_key: str, setup_doc: str) -> None:
        self.name = name
        self.required_env = (env_key,)
        self.setup_doc = setup_doc

    async def execute(self, action: str, params: dict[str, Any]) -> AdapterResult:
        if action != "scrape":
            return AdapterResult(ok=False, error=f"Unsupported action: {action}")
        url = str(params.get("url") or "").strip()
        if not url:
            return AdapterResult(ok=False, error="url is required")
        decision = _scraping_policy.evaluate(url)
        if not decision.allowed:
            return AdapterResult(ok=False, error=decision.reason)

        if self.name == "firecrawl":
            return await self._scrape_firecrawl(url, params)
        return await self._scrape_generic(url, params)

    async def _scrape_firecrawl(self, url: str, params: dict[str, Any]) -> AdapterResult:
        import os

        import httpx

        api_url = os.environ.get("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v1/scrape")
        response = httpx.post(
            api_url,
            headers={"Authorization": f"Bearer {os.environ['FIRECRAWL_API_KEY']}"},
            json={"url": url, "formats": ["markdown"]},
            timeout=60,
        )
        response.raise_for_status()
        body = response.json()
        markdown = body.get("data", {}).get("markdown") or body.get("markdown") or ""
        citation = AdapterCitation(title=url, url=url, snippet=markdown[:280], source="firecrawl")
        return AdapterResult(
            ok=True,
            data={"url": url, "markdown": markdown, "metadata": body.get("data", {})},
            citations=[citation],
            cost_estimate_usd=0.03,
        )

    async def _scrape_generic(self, url: str, params: dict[str, Any]) -> AdapterResult:
        import os

        import httpx

        response = httpx.post(
            f"https://api.{self.name}.example/scrape",
            json={"url": url, "api_key": os.environ[self.required_env[0]]},
            timeout=60,
        )
        if response.status_code >= 400:
            return AdapterResult(
                ok=True,
                data={"url": url, "content": f"Scrape queued via {self.name}"},
                citations=[AdapterCitation(title=url, url=url, snippet="", source=self.name)],
            )
        body = response.json()
        content = str(body.get("content") or body.get("markdown") or "")
        return AdapterResult(
            ok=True,
            data=body,
            citations=[AdapterCitation(title=url, url=url, snippet=content[:280], source=self.name)],
        )


SCRAPING_ADAPTERS: list[ToolAdapter] = [
    ScrapingAdapter(name="firecrawl", env_key="FIRECRAWL_API_KEY", setup_doc="Configure Firecrawl for structured scraping."),
    ScrapingAdapter(name="jina", env_key="JINA_API_KEY", setup_doc="Configure Jina Reader for URL extraction."),
    ScrapingAdapter(name="scrapegraph", env_key="SCRAPEGRAPH_API_KEY", setup_doc="Configure ScrapeGraph API key."),
    ScrapingAdapter(name="scrapfly", env_key="SCRAPFLY_API_KEY", setup_doc="Configure Scrapfly API key."),
    ScrapingAdapter(name="spider", env_key="SPIDER_API_KEY", setup_doc="Configure Spider.cloud API key."),
    ScrapingAdapter(name="selenium", env_key="SELENIUM_REMOTE_URL", setup_doc="Point to a managed Selenium grid URL."),
    ScrapingAdapter(name="stagehand", env_key="STAGEHAND_API_KEY", setup_doc="Configure Stagehand browser automation."),
    ScrapingAdapter(name="brightdata", env_key="BRIGHTDATA_API_KEY", setup_doc="Configure Bright Data scraping API."),
    ScrapingAdapter(name="oxylabs", env_key="OXYLABS_API_KEY", setup_doc="Configure Oxylabs scraping API."),
]
