"""SEO analysis and on-page recommendations for PRISM."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from keprix.compat import UTC, StrEnum
from html import unescape
from typing import Any
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup

from keprix.browser.action_engine import get_action_engine
from keprix.memory.rag.indexer import RagIndexer
from keprix.personas.prism.persona import PRISM_PERSONA
from keprix.research.fetch import MAX_FETCH_BYTES, _is_safe_url

BLACK_HAT_TERMS = (
    "cloaking",
    "link scheme",
    "link schemes",
    "keyword stuffing",
    "hidden text",
    "private blog network",
    "pbn",
    "link farm",
    "doorway page",
    "doorway pages",
    "paid links",
    "article spinning",
    "spamdexing",
)


class ImpactLevel(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class EffortLevel(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass(slots=True)
class SeoRecommendation:
    category: str
    change: str
    why: str
    impact: str
    effort: str
    priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "change": self.change,
            "why": self.why,
            "impact": self.impact,
            "effort": self.effort,
            "priority": self.priority,
        }


@dataclass
class SeoAuditReport:
    audit_id: str
    url: str
    audited_at: str
    overall_health: str
    summary: str
    signals: dict[str, Any] = field(default_factory=dict)
    recommendations: list[SeoRecommendation] = field(default_factory=list)
    render_check: dict[str, Any] = field(default_factory=dict)
    indexed_chunks: int = 0
    markdown: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "url": self.url,
            "audited_at": self.audited_at,
            "overall_health": self.overall_health,
            "summary": self.summary,
            "signals": self.signals,
            "recommendations": [rec.to_dict() for rec in self.recommendations],
            "render_check": self.render_check,
            "indexed_chunks": self.indexed_chunks,
            "markdown": self.markdown,
        }


@dataclass
class ContentBrief:
    brief_id: str
    primary_keyword: str
    intent: str
    target_url: str
    search_volume: int
    difficulty: int
    objective: str
    audience: str
    recommended_title: str
    meta_description: str
    outline: list[str]
    internal_links: list[str]
    competitor_gap: str
    success_metrics: list[str]
    markdown: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "brief_id": self.brief_id,
            "primary_keyword": self.primary_keyword,
            "intent": self.intent,
            "target_url": self.target_url,
            "search_volume": self.search_volume,
            "difficulty": self.difficulty,
            "objective": self.objective,
            "audience": self.audience,
            "recommended_title": self.recommended_title,
            "meta_description": self.meta_description,
            "outline": list(self.outline),
            "internal_links": list(self.internal_links),
            "competitor_gap": self.competitor_gap,
            "success_metrics": list(self.success_metrics),
            "markdown": self.markdown,
        }


def contains_black_hat(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in BLACK_HAT_TERMS)


def filter_white_hat_recommendations(recommendations: list[SeoRecommendation]) -> list[SeoRecommendation]:
    return [
        rec
        for rec in recommendations
        if not contains_black_hat(f"{rec.change} {rec.why}")
    ]


def _priority_score(impact: str, effort: str) -> int:
    impact_rank = {ImpactLevel.HIGH: 3, ImpactLevel.MEDIUM: 2, ImpactLevel.LOW: 1}.get(impact, 1)
    effort_rank = {EffortLevel.LOW: 3, EffortLevel.MEDIUM: 2, EffortLevel.HIGH: 1}.get(effort, 1)
    return impact_rank * 10 + effort_rank


def parse_html_signals(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    title = unescape(title_tag.get_text(strip=True)) if title_tag else ""

    meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    meta_description = unescape(meta_desc_tag.get("content", "").strip()) if meta_desc_tag else ""

    robots_tag = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    robots = unescape(robots_tag.get("content", "").strip()) if robots_tag else ""

    canonical_tag = soup.find("link", attrs={"rel": re.compile(r"canonical", re.I)})
    canonical = canonical_tag.get("href", "").strip() if canonical_tag else ""

    viewport_tag = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    viewport = viewport_tag.get("content", "").strip() if viewport_tag else ""

    h1_tags = soup.find_all("h1")
    h1_texts = [unescape(tag.get_text(strip=True)) for tag in h1_tags if tag.get_text(strip=True)]

    json_ld_blocks: list[dict[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                json_ld_blocks.extend(item for item in parsed if isinstance(item, dict))
            elif isinstance(parsed, dict):
                json_ld_blocks.append(parsed)
        except json.JSONDecodeError:
            continue

    images = soup.find_all("img")
    images_missing_alt = sum(1 for img in images if not (img.get("alt") or "").strip())

    og_title_tag = soup.find("meta", property="og:title")
    og_title = og_title_tag.get("content", "").strip() if og_title_tag else ""

    return {
        "title": title,
        "meta_description": meta_description,
        "robots": robots,
        "canonical": canonical,
        "viewport": viewport,
        "h1_count": len(h1_tags),
        "h1_texts": h1_texts,
        "structured_data_count": len(json_ld_blocks),
        "structured_data_types": sorted(
            {str(block.get("@type", "Unknown")) for block in json_ld_blocks if block.get("@type")}
        ),
        "images_total": len(images),
        "images_missing_alt": images_missing_alt,
        "og_title": og_title,
    }


def build_recommendations(signals: dict[str, Any], url: str) -> list[SeoRecommendation]:
    recs: list[SeoRecommendation] = []

    title = signals.get("title", "")
    if not title:
        recs.append(
            SeoRecommendation(
                category="On-page",
                change="Add a unique <title> tag (50-60 characters).",
                why="Search engines use the title as the primary ranking signal and SERP headline.",
                impact=ImpactLevel.HIGH,
                effort=EffortLevel.LOW,
            )
        )
    elif len(title) > 60:
        recs.append(
            SeoRecommendation(
                category="On-page",
                change="Shorten the title tag to 60 characters or fewer.",
                why=f"Current title is {len(title)} characters; long titles truncate in SERPs.",
                impact=ImpactLevel.MEDIUM,
                effort=EffortLevel.LOW,
            )
        )

    meta_description = signals.get("meta_description", "")
    if not meta_description:
        recs.append(
            SeoRecommendation(
                category="On-page",
                change="Add a meta description (120-160 characters) with primary keyword and CTA.",
                why="Meta descriptions improve click-through rate even when not a direct ranking factor.",
                impact=ImpactLevel.MEDIUM,
                effort=EffortLevel.LOW,
            )
        )

    h1_count = int(signals.get("h1_count", 0))
    if h1_count == 0:
        recs.append(
            SeoRecommendation(
                category="On-page",
                change="Add exactly one H1 that matches the page topic and primary keyword.",
                why="A clear H1 helps crawlers understand page hierarchy and topic focus.",
                impact=ImpactLevel.HIGH,
                effort=EffortLevel.LOW,
            )
        )
    elif h1_count > 1:
        recs.append(
            SeoRecommendation(
                category="On-page",
                change="Reduce to a single H1; demote extra headings to H2.",
                why=f"Found {h1_count} H1 tags; multiple H1s dilute topical signals.",
                impact=ImpactLevel.MEDIUM,
                effort=EffortLevel.LOW,
            )
        )

    if not signals.get("canonical"):
        recs.append(
            SeoRecommendation(
                category="Technical",
                change=f"Add a canonical link pointing to {url}.",
                why="Canonical tags prevent duplicate-content issues across URL variants.",
                impact=ImpactLevel.MEDIUM,
                effort=EffortLevel.LOW,
            )
        )

    robots = (signals.get("robots") or "").lower()
    if "noindex" in robots:
        recs.append(
            SeoRecommendation(
                category="Technical",
                change="Remove noindex from robots meta unless the page should stay private.",
                why="noindex blocks indexing; organic traffic cannot grow while it is set.",
                impact=ImpactLevel.HIGH,
                effort=EffortLevel.LOW,
            )
        )

    if not signals.get("viewport"):
        recs.append(
            SeoRecommendation(
                category="Technical",
                change="Add a mobile viewport meta tag (width=device-width, initial-scale=1).",
                why="Mobile-friendliness is a ranking factor; viewport meta enables responsive layout.",
                impact=ImpactLevel.HIGH,
                effort=EffortLevel.LOW,
            )
        )

    if int(signals.get("structured_data_count", 0)) == 0:
        recs.append(
            SeoRecommendation(
                category="Technical",
                change="Add JSON-LD structured data (Article, FAQ, or Organization as appropriate).",
                why="Structured data can unlock rich results and improve SERP visibility.",
                impact=ImpactLevel.MEDIUM,
                effort=EffortLevel.MEDIUM,
            )
        )

    missing_alt = int(signals.get("images_missing_alt", 0))
    if missing_alt > 0:
        recs.append(
            SeoRecommendation(
                category="Accessibility",
                change=f"Add descriptive alt text to {missing_alt} image(s).",
                why="Alt text improves accessibility and image search visibility.",
                impact=ImpactLevel.LOW,
                effort=EffortLevel.LOW,
            )
        )

    for rec in recs:
        rec.priority = _priority_score(rec.impact, rec.effort)
    recs.sort(key=lambda row: row.priority, reverse=True)
    return filter_white_hat_recommendations(recs)


def _overall_health(recommendations: list[SeoRecommendation]) -> str:
    high_impact = sum(1 for rec in recommendations if rec.impact == ImpactLevel.HIGH)
    if high_impact >= 3:
        return "Poor"
    if high_impact >= 1:
        return "Needs work"
    if recommendations:
        return "Good"
    return "Excellent"


async def fetch_page_html(url: str) -> str:
    normalized = url.strip()
    if not _is_safe_url(normalized):
        raise ValueError(f"URL blocked by SSRF policy: {url}")

    async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
        response = await client.get(
            normalized,
            headers={"User-Agent": "Keprix-SEO/1.0"},
        )
        response.raise_for_status()
        return response.content[:MAX_FETCH_BYTES].decode("utf-8", errors="replace")


class PrismSeo:
    def __init__(self, *, workspace_id: str = "default", user_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = PRISM_PERSONA
        self._indexer = RagIndexer()
        self._audit_template = self.persona.prompts_dir / "seo_audit.md"
        self._brief_template = self.persona.prompts_dir / "content_brief.md"

    def run_render_check(self, url: str) -> dict[str, Any]:
        engine = get_action_engine()
        session = engine.create_session(objective=f"SEO render check for {url}", url=url)
        result = engine.run_action(session.session_id, action="read_page")
        world = result.get("world", {})
        visible = world.get("visible_elements", [])
        return {
            "session_id": session.session_id,
            "status": result.get("status", "unknown"),
            "visible_element_count": len(visible),
            "rendered": len(visible) > 0,
        }

    async def audit_page(
        self,
        url: str,
        *,
        html_content: str | None = None,
        use_browser: bool = True,
        index_to_rag: bool = True,
    ) -> SeoAuditReport:
        audit_id = str(uuid4())
        audited_at = datetime.now(UTC).isoformat()

        html = html_content if html_content is not None else await fetch_page_html(url)
        signals = parse_html_signals(html)
        recommendations = build_recommendations(signals, url)
        health = _overall_health(recommendations)

        render_check: dict[str, Any] = {"skipped": True}
        if use_browser and html_content is None:
            try:
                render_check = self.run_render_check(url)
            except Exception as exc:
                render_check = {"error": str(exc), "rendered": False}

        if render_check.get("rendered") is False and not render_check.get("skipped"):
            recommendations.insert(
                0,
                SeoRecommendation(
                    category="Technical",
                    change="Investigate JavaScript rendering; page may not expose content to crawlers.",
                    why="Browser render check found no visible DOM elements.",
                    impact=ImpactLevel.HIGH,
                    effort=EffortLevel.HIGH,
                    priority=_priority_score(ImpactLevel.HIGH, EffortLevel.HIGH),
                ),
            )

        summary = (
            f"Audited {url}: {len(recommendations)} recommendation(s), "
            f"health={health}, H1={signals.get('h1_count', 0)}, "
            f"structured data blocks={signals.get('structured_data_count', 0)}."
        )
        markdown = self._render_audit_markdown(
            url=url,
            audited_at=audited_at,
            overall_health=health,
            summary=summary,
            signals=signals,
            recommendations=recommendations,
        )

        report = SeoAuditReport(
            audit_id=audit_id,
            url=url,
            audited_at=audited_at,
            overall_health=health,
            summary=summary,
            signals=signals,
            recommendations=recommendations,
            render_check=render_check,
            markdown=markdown,
        )

        if index_to_rag:
            metadata = (
                f"<!-- prism-seo-audit id={audit_id} url={url} "
                f"health={health} indexed_at={audited_at} -->\n"
            )
            report.indexed_chunks = await self._indexer.ingest(
                user_id=self.user_id,
                source_type="prism_seo_audit",
                source_id=audit_id,
                content=metadata + markdown,
            )

        return report

    def build_content_brief(
        self,
        *,
        primary_keyword: str,
        intent: str,
        target_url: str,
        search_volume: int,
        difficulty: int,
        audience: str = "Searchers looking for practical answers",
        competitor_gap: str = "Competitors lack actionable checklists and updated examples.",
        internal_links: list[str] | None = None,
    ) -> ContentBrief:
        brief_id = str(uuid4())
        recommended_title = f"{primary_keyword.title()}: Practical Guide ({datetime.now(UTC).year})"
        meta_description = (
            f"Learn {primary_keyword} with clear steps, examples, and metrics. "
            f"Updated guide for teams focused on organic growth."
        )[:160]
        outline = [
            f"What is {primary_keyword}?",
            f"Why {primary_keyword} matters for organic growth",
            f"Step-by-step {primary_keyword} workflow",
            "Common mistakes and how to fix them",
            "Metrics to track and next steps",
        ]
        success_metrics = [
            f"Rank top 20 for '{primary_keyword}' within 90 days",
            "Increase organic sessions by 15% quarter over quarter",
            "Improve average position for supporting keywords",
        ]
        links = internal_links or ["/resources", "/blog", "/contact"]

        markdown = self._render_brief_markdown(
            primary_keyword=primary_keyword,
            intent=intent,
            target_url=target_url,
            search_volume=search_volume,
            difficulty=difficulty,
            objective=f"Rank for '{primary_keyword}' and convert informational traffic.",
            audience=audience,
            recommended_title=recommended_title,
            meta_description=meta_description,
            outline=outline,
            internal_links=links,
            competitor_gap=competitor_gap,
            success_metrics=success_metrics,
        )

        return ContentBrief(
            brief_id=brief_id,
            primary_keyword=primary_keyword,
            intent=intent,
            target_url=target_url,
            search_volume=search_volume,
            difficulty=difficulty,
            objective=f"Rank for '{primary_keyword}' and convert informational traffic.",
            audience=audience,
            recommended_title=recommended_title,
            meta_description=meta_description,
            outline=outline,
            internal_links=links,
            competitor_gap=competitor_gap,
            success_metrics=success_metrics,
            markdown=markdown,
        )

    def _render_audit_markdown(
        self,
        *,
        url: str,
        audited_at: str,
        overall_health: str,
        summary: str,
        signals: dict[str, Any],
        recommendations: list[SeoRecommendation],
    ) -> str:
        rows = []
        for rec in recommendations:
            rows.append(
                f"| {rec.priority} | {rec.category} | {rec.change} | {rec.impact} | {rec.effort} | {rec.why} |"
            )
        finding_rows = "\n".join(rows) if rows else "| - | - | No issues found | - | - | - |"
        actions = "\n".join(f"{index}. [{rec.impact}/{rec.effort}] {rec.change}" for index, rec in enumerate(recommendations, 1))
        template = self._audit_template.read_text(encoding="utf-8")
        return (
            template.replace("{{url}}", url)
            .replace("{{audited_at}}", audited_at)
            .replace("{{overall_health}}", overall_health)
            .replace("{{summary}}", summary)
            .replace("{{finding_rows}}", finding_rows)
            .replace("{{title}}", signals.get("title", "(missing)"))
            .replace("{{meta_description}}", signals.get("meta_description", "(missing)"))
            .replace("{{h1_count}}", str(signals.get("h1_count", 0)))
            .replace("{{structured_data}}", ", ".join(signals.get("structured_data_types", [])) or "none")
            .replace("{{viewport}}", signals.get("viewport", "(missing)"))
            .replace("{{prioritised_actions}}", actions or "No actions required.")
        )

    def _render_brief_markdown(
        self,
        *,
        primary_keyword: str,
        intent: str,
        target_url: str,
        search_volume: int,
        difficulty: int,
        objective: str,
        audience: str,
        recommended_title: str,
        meta_description: str,
        outline: list[str],
        internal_links: list[str],
        competitor_gap: str,
        success_metrics: list[str],
    ) -> str:
        template = self._brief_template.read_text(encoding="utf-8")
        outline_text = "\n".join(f"{index}. {item}" for index, item in enumerate(outline, 1))
        metrics_text = "\n".join(f"- {metric}" for metric in success_metrics)
        return (
            template.replace("{{primary_keyword}}", primary_keyword)
            .replace("{{intent}}", intent)
            .replace("{{target_url}}", target_url)
            .replace("{{search_volume}}", str(search_volume))
            .replace("{{difficulty}}", str(difficulty))
            .replace("{{objective}}", objective)
            .replace("{{audience}}", audience)
            .replace("{{recommended_title}}", recommended_title)
            .replace("{{meta_description}}", meta_description)
            .replace("{{outline}}", outline_text)
            .replace("{{internal_links}}", ", ".join(internal_links))
            .replace("{{competitor_gap}}", competitor_gap)
            .replace("{{success_metrics}}", metrics_text)
        )
