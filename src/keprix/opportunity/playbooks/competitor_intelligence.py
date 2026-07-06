"""Competitor Intelligence playbook for the Opportunity Engine."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from keprix.opportunity.citations import add_citation, list_citations
from keprix.opportunity.safety import SafetyViolation, run_content_safety_checks, validate_research_url
from keprix.opportunity.workspace import read_artifact, read_opportunity_json, update_opportunity_json, write_artifact
from keprix.research.search import web_search

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_MIN_COMPETITORS = 5

_PRIVATE_SOURCE_RE = re.compile(
    r"\b(private message|dm me|members only|login required|paywall|invite only)\b",
    re.I,
)
_PRICING_RE = re.compile(r"\b(\$|£|€|\d+\s*/\s*mo|per month|pricing|subscription)\b", re.I)
_PROOF_RE = re.compile(r"\b(case study|testimonial|customer story|trusted by|clients include)\b", re.I)
_ADJACENT_RE = re.compile(r"\b(alternative|adjacent|related|also bought|category)\b", re.I)


class CompetitorIntelligenceInput(BaseModel):
    niche: str
    icp_summary: str = ""
    offer_name: str = ""
    geography: str | None = None
    competitor_seeds: list[str] = Field(default_factory=list)
    banned_domains: list[str] = Field(default_factory=list)
    research_depth: Literal["quick", "standard", "deep"] = "standard"


class FunnelArchitecture(BaseModel):
    traffic_source: str = ""
    landing_promise: str = ""
    lead_magnet: str = ""
    cta: str = ""
    checkout_path: str = ""
    nurture_hints: str = ""
    trust_proof: str = ""
    objections_handled: str = ""
    follow_up: str = ""


class CompetitorRecord(BaseModel):
    name: str
    domain: str
    segment: Literal["direct", "adjacent"] = "direct"
    offer: str = ""
    icp: str = ""
    pricing_signal: str = ""
    pricing_verified: bool = False
    funnel_type: str = ""
    proof: str = ""
    weakness: str = ""
    market_strength: float = 0.0
    funnel_quality: float = 0.0
    proof_strength: float = 0.0
    differentiation_gap: float = 0.0
    funnel: FunnelArchitecture = Field(default_factory=FunnelArchitecture)
    citation_urls: list[str] = Field(default_factory=list)
    source_kind: str = "web_search"


@dataclass
class CompetitorSignal:
    title: str
    url: str
    snippet: str
    source_kind: str
    seed: str = ""


def _domain_from_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def is_private_source(text: str, url: str = "") -> bool:
    if _PRIVATE_SOURCE_RE.search(text):
        return True
    lowered = url.lower()
    if any(token in lowered for token in ("/login", "/signin", "/private", "/members")):
        return True
    return False


def merge_duplicate_competitors(competitors: list[CompetitorRecord]) -> list[CompetitorRecord]:
    merged: dict[str, CompetitorRecord] = {}
    for row in competitors:
        key = row.domain or row.name.lower().strip()
        if not key:
            continue
        if key in merged:
            existing = merged[key]
            for url in row.citation_urls:
                if url not in existing.citation_urls:
                    existing.citation_urls.append(url)
            existing.market_strength = max(existing.market_strength, row.market_strength)
            existing.funnel_quality = max(existing.funnel_quality, row.funnel_quality)
            existing.proof_strength = max(existing.proof_strength, row.proof_strength)
            if row.proof and not existing.proof:
                existing.proof = row.proof
            if row.pricing_signal and not existing.pricing_signal:
                existing.pricing_signal = row.pricing_signal
        else:
            merged[key] = row
    return list(merged.values())


def validate_competitor_citations(competitors: list[CompetitorRecord]) -> list[str]:
    issues: list[str] = []
    for row in competitors:
        factual = row.pricing_signal or row.proof or row.offer
        if factual and not row.citation_urls:
            issues.append(row.name)
    return issues


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, round(value, 1)))


def _score_competitor(signal: CompetitorSignal, *, icp_summary: str) -> dict[str, float]:
    text = f"{signal.title} {signal.snippet}"
    market = 40.0 + (20.0 if signal.title else 0.0) + (10.0 if len(signal.snippet) > 80 else 0.0)
    funnel = 35.0 + (15.0 if "landing" in text.lower() or "demo" in text.lower() else 0.0)
    proof = 30.0 + (25.0 if _PROOF_RE.search(text) else 0.0)
    gap = 50.0 + (15.0 if icp_summary and icp_summary.lower() not in text.lower() else 0.0)
    if _ADJACENT_RE.search(text):
        gap += 10.0
    return {
        "market_strength": _clamp(market),
        "funnel_quality": _clamp(funnel),
        "proof_strength": _clamp(proof),
        "differentiation_gap": _clamp(gap),
    }


def _competitor_name(signal: CompetitorSignal) -> str:
    title = signal.title.strip()
    if title:
        return title.split("|")[0].split("-")[0].strip()[:80]
    domain = _domain_from_url(signal.url)
    return domain or "Unknown competitor"


def _is_banned(url: str, banned: list[str]) -> bool:
    domain = _domain_from_url(url)
    return any(term.lower() in domain or term.lower() in url.lower() for term in banned)


def _search_queries(inp: CompetitorIntelligenceInput) -> list[tuple[str, str]]:
    geo = f" {inp.geography}" if inp.geography else ""
    base = inp.niche
    icp = inp.icp_summary[:60] if inp.icp_summary else ""
    queries = [
        (f"{base}{geo} competitors software", "search"),
        (f"{base}{geo} alternatives {icp}", "alternatives"),
        (f"{base}{geo} pricing landing page", "landing"),
        (f"{base}{geo} case study customers", "proof"),
        (f"{base}{geo} reviews g2 capterra", "reviews"),
        (f"{base}{geo} marketplace listing", "marketplace"),
        (f"{base}{geo} facebook ad library hooks", "ads"),
    ]
    for seed in inp.competitor_seeds[:3]:
        queries.insert(0, (f"{seed} {base} positioning pricing", "seed"))
    depth_limits = {"quick": 3, "standard": 5, "deep": 7}
    return queries[: depth_limits[inp.research_depth]]


async def _gather_competitor_signals(inp: CompetitorIntelligenceInput) -> list[CompetitorSignal]:
    signals: list[CompetitorSignal] = []
    seen_urls: set[str] = set()
    per_query = {"quick": 3, "standard": 5, "deep": 5}[inp.research_depth]

    for query, kind in _search_queries(inp):
        results = await web_search(query, limit=per_query)
        for item in results:
            url = str(item.get("url", "")).strip()
            snippet = str(item.get("snippet", ""))
            if not url or url in seen_urls or _is_banned(url, inp.banned_domains):
                continue
            if is_private_source(snippet, url):
                continue
            try:
                validate_research_url(url)
            except SafetyViolation:
                continue
            seen_urls.add(url)
            signals.append(
                CompetitorSignal(
                    title=str(item.get("title", "")),
                    url=url,
                    snippet=snippet,
                    source_kind=kind,
                ),
            )
    return signals


def _signal_to_competitor(signal: CompetitorSignal, inp: CompetitorIntelligenceInput) -> CompetitorRecord:
    scores = _score_competitor(signal, icp_summary=inp.icp_summary)
    text = f"{signal.title} {signal.snippet}"
    segment: Literal["direct", "adjacent"] = "adjacent" if _ADJACENT_RE.search(text) else "direct"
    pricing_verified = bool(_PRICING_RE.search(text))
    pricing_signal = "Unverified" 
    if pricing_verified:
        pricing_signal = "Public pricing mention (verify on site)"
    funnel = FunnelArchitecture(
        traffic_source="Search or paid social (inferred)" if segment == "direct" else "Content/SEO (inferred)",
        landing_promise=signal.snippet[:120] or signal.title,
        lead_magnet="Guide or checklist (inferred)" if "guide" in text.lower() else "Not visible",
        cta="Book demo / Start trial (inferred)",
        checkout_path="Self-serve signup or sales call",
        nurture_hints="Email sequence (inferred)" if "email" in text.lower() else "Unknown",
        trust_proof="Case studies mentioned" if _PROOF_RE.search(text) else "Limited public proof",
        objections_handled="ROI and security pages (inferred)",
        follow_up="Sales outreach (inferred)",
    )
    return CompetitorRecord(
        name=_competitor_name(signal),
        domain=_domain_from_url(signal.url),
        segment=segment,
        offer=signal.title[:100],
        icp=inp.icp_summary[:80] or inp.niche,
        pricing_signal=pricing_signal,
        pricing_verified=pricing_verified,
        funnel_type="Product-led" if "trial" in text.lower() else "Sales-led",
        proof="Public proof found" if _PROOF_RE.search(text) else "Weak public proof",
        weakness="Generic positioning" if segment == "adjacent" else "May lack governed approval workflow",
        funnel=funnel,
        citation_urls=[signal.url],
        source_kind=signal.source_kind,
        **scores,
    )


def _fallback_competitors(inp: CompetitorIntelligenceInput, count: int) -> list[CompetitorRecord]:
    rows: list[CompetitorRecord] = []
    for idx in range(1, count + 1):
        rows.append(
            CompetitorRecord(
                name=f"Inferred competitor {idx}",
                domain="",
                segment="adjacent",
                offer=f"Adjacent tool in {inp.niche}",
                icp=inp.icp_summary or inp.niche,
                pricing_signal="Unverified",
                pricing_verified=False,
                funnel_type="Unknown",
                proof="No public citation",
                weakness="Insufficient public data",
                market_strength=20.0,
                funnel_quality=20.0,
                proof_strength=15.0,
                differentiation_gap=60.0,
                citation_urls=[],
            ),
        )
    return rows


def _render_report(
    *,
    competitors: list[CompetitorRecord],
    differentiation: str,
) -> str:
    template = (_TEMPLATES_DIR / "competitor-intelligence-report.md").read_text(encoding="utf-8")
    rows: list[str] = []
    funnel_blocks: list[str] = []
    lead_magnets: list[str] = []
    ads_hooks: list[str] = []
    case_studies: list[str] = []
    pricing_lines: list[str] = []
    content_lines: list[str] = []
    not_copy: list[str] = [
        "- Competitor guarantees or unverified ROI claims",
        "- Fear-based or predatory messaging",
        "- Opaque pricing patterns you cannot substantiate",
    ]

    for comp in competitors:
        rows.append(
            "| {name} | {seg} | {offer} | {icp} | {price} | {funnel} | {proof} | {weak} |".format(
                name=comp.name.replace("|", "/")[:40],
                seg=comp.segment,
                offer=comp.offer.replace("|", "/")[:40],
                icp=comp.icp.replace("|", "/")[:30],
                price=comp.pricing_signal.replace("|", "/")[:30],
                funnel=comp.funnel_type,
                proof=comp.proof.replace("|", "/")[:30],
                weak=comp.weakness.replace("|", "/")[:30],
            ),
        )
        funnel_blocks.append(
            f"### {comp.name}\n"
            f"- Traffic: {comp.funnel.traffic_source}\n"
            f"- Promise: {comp.funnel.landing_promise}\n"
            f"- Lead magnet: {comp.funnel.lead_magnet}\n"
            f"- CTA: {comp.funnel.cta}\n"
            f"- Checkout path: {comp.funnel.checkout_path}\n"
            f"- Nurture: {comp.funnel.nurture_hints}\n"
            f"- Trust proof: {comp.funnel.trust_proof}\n"
            f"- Objections: {comp.funnel.objections_handled}\n"
            f"- Follow-up: {comp.funnel.follow_up}\n"
            f"- Scores: market {comp.market_strength}, funnel {comp.funnel_quality}, "
            f"proof {comp.proof_strength}, gap {comp.differentiation_gap}",
        )
        if comp.funnel.lead_magnet != "Not visible":
            lead_magnets.append(f"- {comp.name}: {comp.funnel.lead_magnet}")
        ads_hooks.append(f"- {comp.name}: hooks inferred from public listings and search snippets")
        if _PROOF_RE.search(comp.proof):
            case_studies.append(f"- {comp.name}: {comp.proof}")
        flag = " (unverified)" if not comp.pricing_verified else ""
        pricing_lines.append(f"- {comp.name}: {comp.pricing_signal}{flag}")
        content_lines.append(f"- {comp.name}: category content and comparison pages (public)")

    citations: list[str] = []
    for index, comp in enumerate(competitors, start=1):
        for url in comp.citation_urls:
            citations.append(f"{index}. {comp.name}: {url}")
    if not citations:
        citations.append("No external citations captured; treat competitor map as weak inference.")

    replacements = {
        "{{competitor_rows}}": "\n".join(rows),
        "{{funnel_architecture}}": "\n".join(funnel_blocks) or "- No funnel data captured.",
        "{{lead_magnets}}": "\n".join(lead_magnets) or "- None identified from public sources.",
        "{{ads_and_hooks}}": "\n".join(ads_hooks) or "- No public ad library data captured.",
        "{{case_studies}}": "\n".join(case_studies) or "- No verified public case studies found.",
        "{{pricing_signals}}": "\n".join(pricing_lines) or "- All pricing unverified.",
        "{{content_strategy}}": "\n".join(content_lines) or "- Unknown.",
        "{{differentiation}}": differentiation,
        "{{what_not_to_copy}}": "\n".join(not_copy),
        "{{citations}}": "\n".join(citations),
    }
    report = template
    for key, value in replacements.items():
        report = report.replace(key, value)
    return report


def build_competitor_intelligence_input_from_meta(
    meta: dict[str, Any],
    *,
    icp_md: str = "",
    offer_md: str = "",
) -> CompetitorIntelligenceInput:
    icp = meta.get("icp", {}).get("primary", {})
    icp_summary = str(icp.get("summary") or "")
    if not icp_summary and icp_md:
        idx = icp_md.find("## Primary ICP")
        if idx >= 0:
            icp_summary = icp_md[idx : idx + 200].splitlines()[2:3]
            icp_summary = icp_summary[0].strip("* ") if icp_summary else ""
    offer = meta.get("offer", {})
    offer_name = str(offer.get("offer_name") or "")
    if not offer_name and offer_md:
        idx = offer_md.find("## Offer Name")
        if idx >= 0:
            lines = offer_md[idx:].splitlines()
            if len(lines) > 2:
                offer_name = lines[2].strip()
    depth = meta.get("research_depth", "standard")
    if depth not in {"quick", "standard", "deep"}:
        depth = "standard"
    return CompetitorIntelligenceInput(
        niche=str(meta.get("niche") or meta.get("title") or "market"),
        icp_summary=icp_summary,
        offer_name=offer_name,
        geography=meta.get("geography"),
        competitor_seeds=list(meta.get("competitor_seeds") or []),
        banned_domains=list(meta.get("banned_domains") or meta.get("banned_sources") or []),
        research_depth=depth,
    )


async def run_competitor_intelligence_playbook(
    *,
    workspace_id: str,
    opportunity_id: str,
    request: CompetitorIntelligenceInput,
) -> str:
    signals = await _gather_competitor_signals(request)
    competitors = [_signal_to_competitor(signal, request) for signal in signals]
    competitors = merge_duplicate_competitors(competitors)

    if len(competitors) < _MIN_COMPETITORS:
        competitors.extend(_fallback_competitors(request, _MIN_COMPETITORS - len(competitors)))

    citation_issues = validate_competitor_citations(competitors)
    for comp in competitors:
        if comp.name in citation_issues:
            comp.pricing_signal = "Unverified"
            comp.pricing_verified = False

    for signal in signals:
        add_citation(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            url=signal.url,
            title=signal.title,
            snippet=signal.snippet,
            phase="competitor_intelligence",
            artifact_filename="04-competitors.md",
            source=signal.source_kind,
        )

    top_gap = max(competitors, key=lambda row: row.differentiation_gap, default=None)
    differentiation = (
        f"Lead with governed validation playbooks and explicit approval gates, "
        f"especially where competitors like {top_gap.name if top_gap else 'incumbents'} "
        f"show weak public proof or unverified pricing."
    )

    report = _render_report(competitors=competitors, differentiation=differentiation)
    run_content_safety_checks(
        opportunity_id=opportunity_id,
        text=report,
        require_citations=bool(signals),
    )

    write_artifact(opportunity_id, "04-competitors.md", report)
    citations = [cite.model_dump(mode="json") for cite in list_citations(opportunity_id)]
    update_opportunity_json(
        opportunity_id,
        {
            "phase": "competitor_intelligence",
            "status": "researching",
            "competitors": [comp.model_dump() for comp in competitors],
            "differentiation_recommendation": differentiation,
            "citations": citations,
        },
    )
    return report
