"""Workflow 4: SEO Agent.

INPUT: keywords + website
  → competitor angles → outline → draft → internal links → ranking checklist
OUTPUT: SEO article package ready to publish and monitor
"""

from __future__ import annotations

import re
from typing import Any


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "seo-article"


def generate_seo_package(
    *,
    keywords: str,
    website: str = "",
    title: str | None = None,
) -> dict[str, Any]:
    raw_keywords = [k.strip() for k in re.split(r"[,|\n]", keywords or "") if k.strip()]
    primary = raw_keywords[0] if raw_keywords else "untitled topic"
    secondary = raw_keywords[1:] or [f"{primary} examples", f"{primary} checklist"]
    site = (website or "").strip() or "https://example.com"
    article_title = (title or "").strip() or f"{primary.title()}: a practical guide"

    competitors = [
        {
            "angle": f"Definition-first explainer for {primary}",
            "gap": "Weak on actionable checklists and agent workflows.",
        },
        {
            "angle": f"Tool roundup around {primary}",
            "gap": "Lists tools without an end-to-end publish path.",
        },
        {
            "angle": f"Case study / opinion on {primary}",
            "gap": "Low internal linking and thin FAQs.",
        },
    ]

    outline = [
        f"What {primary} really means",
        f"Why {primary} fails for most teams",
        f"A step-by-step {primary} workflow",
        f"Templates and examples for {primary}",
        "Internal links and next actions",
        "FAQ",
    ]

    sections = []
    for heading in outline:
        sections.append(
            {
                "heading": heading,
                "body": (
                    f"Cover {heading.lower()} with concrete language about {primary}. "
                    f"Include one example tied to {site} and one secondary keyword "
                    f"({secondary[0]})."
                ),
            }
        )

    draft_parts = [f"# {article_title}", ""]
    for section in sections:
        draft_parts.extend([f"## {section['heading']}", "", section["body"], ""])
    draft_parts.extend(
        [
            "## FAQ",
            "",
            f"### What is {primary}?",
            f"{primary.title()} is the practice of producing searchable, useful content that earns rankings and conversions.",
            "",
            f"### How do I start {primary} this week?",
            "Pick one keyword cluster, publish one article, add three internal links, then measure impressions after 7-14 days.",
        ]
    )
    draft = "\n".join(draft_parts)

    internal_links = [
        {"anchor": primary, "suggested_url": f"{site.rstrip('/')}/blog/{_slug(primary)}"},
        {"anchor": secondary[0], "suggested_url": f"{site.rstrip('/')}/resources/{_slug(secondary[0])}"},
        {"anchor": "getting started", "suggested_url": f"{site.rstrip('/')}/docs/getting-started"},
    ]

    ranking_checklist = [
        "Publish the article with primary keyword in title + H1",
        "Add meta description under 155 characters",
        "Insert 2-4 internal links",
        "Submit URL in Search Console / index request",
        "Monitor impressions and CTR on day 7 and day 30",
    ]

    steps = [
        {"id": "research", "title": "Competitor angle map", "status": "done"},
        {"id": "outline", "title": "Content outline", "status": "done"},
        {"id": "draft", "title": "SEO draft", "status": "done"},
        {"id": "links", "title": "Internal linking plan", "status": "done"},
        {"id": "publish", "title": "Human publish + rank monitor", "status": "todo"},
    ]

    markdown = [
        f"# SEO package: {article_title}",
        "",
        f"Primary keyword: `{primary}`",
        f"Secondary: {', '.join(f'`{k}`' for k in secondary)}",
        f"Website: {site}",
        "",
        "## Competitor gaps",
        *[f"- {row['angle']}: {row['gap']}" for row in competitors],
        "",
        "## Outline",
        *[f"1. {item}" for item in outline],
        "",
        "## Draft",
        "",
        draft,
        "",
        "## Internal links",
        *[f"- [{link['anchor']}]({link['suggested_url']})" for link in internal_links],
        "",
        "## Ranking checklist",
        *[f"- [ ] {item}" for item in ranking_checklist],
    ]

    return {
        "status": "ok",
        "workflow": "seo-agent",
        "primary_keyword": primary,
        "secondary_keywords": secondary,
        "website": site,
        "title": article_title,
        "competitors": competitors,
        "outline": outline,
        "draft": draft,
        "internal_links": internal_links,
        "ranking_checklist": ranking_checklist,
        "steps": steps,
        "output": "\n".join(markdown),
        "artifact": {
            "type": "seo_package",
            "primary_keyword": primary,
            "slug": _slug(article_title),
            "auto_skill": True,
        },
    }
