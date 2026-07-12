"""SEO Agent entrypoint."""
from __future__ import annotations
from typing import Any
from keprix.agent_os.workflows.seo_agent import generate_seo_package

def run(input_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    form = (context or {}).get("form") or {}
    keywords = str(form.get("keywords") or input_text or "").strip()
    website = str(form.get("website") or "https://example.com")
    title = form.get("title")
    return generate_seo_package(keywords=keywords, website=website, title=str(title) if title else None)
