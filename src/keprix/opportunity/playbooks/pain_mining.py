"""Pain Mining playbook for the Opportunity Engine."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from keprix.opportunity.citations import add_citation, list_citations
from keprix.opportunity.safety import SafetyViolation, run_content_safety_checks, validate_research_url
from keprix.opportunity.workspace import read_artifact, read_opportunity_json, update_opportunity_json, write_artifact
from keprix.research.search import web_search

ResearchDepth = Literal["quick", "standard", "deep"]

_DEPTH_CONFIG: dict[ResearchDepth, dict[str, int]] = {
    "quick": {"queries": 3, "results_per_query": 3, "min_pains": 5},
    "standard": {"queries": 5, "results_per_query": 5, "min_pains": 7},
    "deep": {"queries": 8, "results_per_query": 5, "min_pains": 7},
}

_PAIN_WORDS = re.compile(
    r"\b(struggle|frustrat|pain|problem|broken|manual|slow|expensive|waste|can't|cannot|hate|difficult)\b",
    re.I,
)
_URGENCY_WORDS = re.compile(r"\b(urgent|deadline|losing|bleeding|critical|now|asap)\b", re.I)
_COST_WORDS = re.compile(r"\b(cost|revenue|hours|budget|churn|lost|waste)\b", re.I)
_OBJECTION_WORDS = re.compile(r"\b(too expensive|not sure|don't trust|won't|vendor|contract)\b", re.I)
_EMOTION_WORDS = re.compile(r"\b(stress|overwhelm|burnout|anxious|fear|worried)\b", re.I)
_COMPLIANCE_WORDS = re.compile(
    r"\b(gdpr|hipaa|compliance|regulation|privacy|legal|ethical|consent)\b",
    re.I,
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_MAX_QUOTE_LEN = 120


class PainMiningInput(BaseModel):
    demand_pocket: str = Field(..., min_length=1)
    niche: str = Field(..., min_length=1)
    icp_hints: str | None = None
    banned_sources: list[str] = Field(default_factory=list)
    research_depth: ResearchDepth = "standard"


class MarketPain(BaseModel):
    rank: int
    pain: str
    exact_language: str
    evidence: str
    urgency: str
    business_cost: str
    urgency_score: float = 0.0
    citation_url: str = ""
    is_inference: bool = False


@dataclass
class PainSignal:
    title: str
    url: str
    snippet: str
    source_kind: str


def sanitize_quote(text: str, *, source: str) -> str:
    """Strip PII and shorten market-language quotes."""
    cleaned = text.strip()
    cleaned = _EMAIL_RE.sub("[redacted-email]", cleaned)
    cleaned = _PHONE_RE.sub("[redacted-phone]", cleaned)
    cleaned = _SSN_RE.sub("[redacted-id]", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    if len(cleaned) > _MAX_QUOTE_LEN:
        cleaned = cleaned[: _MAX_QUOTE_LEN - 3].rstrip() + "..."
    if not cleaned:
        return f"Paraphrased from {source}"
    return f'"{cleaned}" ({source})'


def _urgency_label(score: float) -> str:
    if score >= 70:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


def _business_cost_label(text: str) -> str:
    if _COST_WORDS.search(text):
        return "Quantified or implied operational cost"
    return "Qualitative time or effort cost"


def _score_signal(signal: PainSignal) -> float:
    text = f"{signal.title} {signal.snippet}"
    score = 30.0
    if _PAIN_WORDS.search(text):
        score += 25.0
    if _URGENCY_WORDS.search(text):
        score += 20.0
    if _COST_WORDS.search(text):
        score += 15.0
    if len(signal.snippet) > 80:
        score += 10.0
    return min(100.0, score)


def rank_pains(pains: list[MarketPain]) -> list[MarketPain]:
    ranked = sorted(pains, key=lambda row: row.urgency_score, reverse=True)
    for index, pain in enumerate(ranked, start=1):
        pain.rank = index
    return ranked


def validate_pain_citations(pains: list[MarketPain]) -> list[str]:
    issues: list[str] = []
    for pain in pains:
        if pain.evidence == "Strong" and not pain.citation_url:
            issues.append(pain.pain)
    return issues


def _selected_demand_pocket(meta: dict[str, Any]) -> str:
    pocket = meta.get("recommended_demand_pocket") or meta.get("selected_demand_pocket")
    if pocket:
        return str(pocket)
    pockets = meta.get("demand_pockets") or []
    if pockets:
        return str(pockets[0].get("name", "Primary demand pocket"))
    return meta.get("niche") or meta.get("title") or "Primary demand pocket"


def _search_queries(inp: PainMiningInput) -> list[tuple[str, str]]:
    pocket = inp.demand_pocket
    niche = inp.niche
    icp = f" {inp.icp_hints}" if inp.icp_hints else ""
    queries = [
        (f"{pocket} {niche}{icp} pain points forum", "forums"),
        (f"{pocket} {niche} frustrated problems reddit", "social"),
        (f"{pocket} {niche} failed alternative software", "alternatives"),
        (f"{pocket} {niche} workaround spreadsheet manual", "workarounds"),
        (f"{pocket} {niche} objections buying", "objections"),
        (f"{pocket} {niche} trust vendor reviews", "trust"),
        (f"{pocket} {niche} compliance risk", "compliance"),
        (f"{pocket} {niche} emotional stress overwhelmed", "emotional"),
    ]
    if inp.banned_sources:
        banned = " ".join(f"-{term}" for term in inp.banned_sources[:3])
        queries = [(f"{q} {banned}", kind) for q, kind in queries]
    limit = _DEPTH_CONFIG[inp.research_depth]["queries"]
    return queries[:limit]


def _is_banned(url: str, banned: list[str]) -> bool:
    lowered = url.lower()
    return any(term.lower() in lowered for term in banned)


async def _gather_pain_signals(inp: PainMiningInput) -> list[PainSignal]:
    config = _DEPTH_CONFIG[inp.research_depth]
    signals: list[PainSignal] = []
    seen: set[str] = set()
    for query, kind in _search_queries(inp):
        results = await web_search(query, limit=config["results_per_query"])
        for item in results:
            url = str(item.get("url", "")).strip()
            if not url or url in seen or _is_banned(url, inp.banned_sources):
                continue
            try:
                validate_research_url(url)
            except SafetyViolation:
                continue
            seen.add(url)
            signals.append(
                PainSignal(
                    title=str(item.get("title", "")),
                    url=url,
                    snippet=str(item.get("snippet", "")),
                    source_kind=kind,
                ),
            )
    return signals


def _pain_from_signal(signal: PainSignal, *, index: int) -> MarketPain:
    snippet = signal.snippet or signal.title
    pain_summary = snippet[:100] or f"Market pain {index}"
    if _PAIN_WORDS.search(snippet):
        pain_summary = pain_summary.split(".")[0][:100]
    urgency_score = _score_signal(signal)
    exact = sanitize_quote(snippet[:200], source=signal.source_kind)
    return MarketPain(
        rank=index,
        pain=pain_summary,
        exact_language=exact,
        evidence="Strong" if signal.url and len(snippet) > 40 else "Moderate",
        urgency=_urgency_label(urgency_score),
        business_cost=_business_cost_label(snippet),
        urgency_score=urgency_score,
        citation_url=signal.url,
        is_inference=False,
    )


def _fallback_pains(inp: PainMiningInput, count: int) -> list[MarketPain]:
    pains: list[MarketPain] = []
    for idx in range(1, count + 1):
        pains.append(
            MarketPain(
                rank=idx,
                pain=f"Inferred pain {idx} for {inp.demand_pocket}",
                exact_language=f"Paraphrased: buyers in {inp.niche} report workflow friction ({inp.demand_pocket})",
                evidence="Weak inference",
                urgency="Low",
                business_cost="Unknown; requires validation",
                urgency_score=20.0,
                citation_url="",
                is_inference=True,
            ),
        )
    return pains


def _extract_phrases(signals: list[PainSignal]) -> list[str]:
    phrases: list[str] = []
    for signal in signals:
        for match in _PAIN_WORDS.finditer(signal.snippet):
            start = max(0, match.start() - 30)
            end = min(len(signal.snippet), match.end() + 40)
            phrase = signal.snippet[start:end].strip()
            if phrase and phrase not in phrases:
                phrases.append(sanitize_quote(phrase, source=signal.source_kind))
    return phrases[:10]


def _section_from_signals(
    signals: list[PainSignal],
    pattern: re.Pattern[str],
    *,
    default: str,
) -> str:
    lines: list[str] = []
    for signal in signals:
        if pattern.search(f"{signal.title} {signal.snippet}"):
            quote = sanitize_quote(signal.snippet[:160], source=signal.source_kind)
            lines.append(f"- {quote}")
    return "\n".join(lines) if lines else default


def _messaging_angles(pains: list[MarketPain]) -> list[str]:
    angles: list[str] = []
    for pain in pains[:5]:
        angles.append(
            f"- Lead with relief for: {pain.pain} (urgency: {pain.urgency.lower()})",
        )
    if not angles:
        angles.append("- Validate top pains with customer interviews before messaging.")
    return angles


def _render_report(
    *,
    inp: PainMiningInput,
    pains: list[MarketPain],
    signals: list[PainSignal],
    objections: list[str],
    messaging_angles: list[str],
) -> str:
    template = (_TEMPLATES_DIR / "pain-mining-report.md").read_text(encoding="utf-8")

    rows: list[str] = []
    for pain in pains:
        rows.append(
            "| {rank} | {pain} | {lang} | {evidence} | {urgency} | {cost} |".format(
                rank=pain.rank,
                pain=pain.pain.replace("|", "/")[:60],
                lang=pain.exact_language.replace("|", "/")[:80],
                evidence=pain.evidence,
                urgency=pain.urgency,
                cost=pain.business_cost.replace("|", "/")[:50],
            ),
        )

    failed = _section_from_signals(
        signals,
        re.compile(r"\b(failed|didn't work|switched away|churned|replaced)\b", re.I),
        default="- No documented failed alternatives found; treat as inference until validated.",
    )
    workarounds = _section_from_signals(
        signals,
        re.compile(r"\b(spreadsheet|manual|workaround|hack|diy|template)\b", re.I),
        default="- Teams may be using spreadsheets or manual processes (inference).",
    )
    emotional = _section_from_signals(
        signals,
        _EMOTION_WORDS,
        default="- Stress and overwhelm are common when operations are manual (inference).",
    )
    trust = _section_from_signals(
        signals,
        re.compile(r"\b(trust|vendor|scam|skeptic|proof|case study)\b", re.I),
        default="- Buyers may require proof and references before switching vendors.",
    )
    compliance = _section_from_signals(
        signals,
        _COMPLIANCE_WORDS,
        default="- Review data handling, consent, and sector regulations before outreach.",
    )

    objection_lines = [f"- {obj}" for obj in objections] or [
        "- Price sensitivity without clear ROI proof",
        "- Fear of migration cost and downtime",
    ]

    citation_lines = []
    for index, pain in enumerate(pains, start=1):
        if pain.citation_url:
            citation_lines.append(f"{index}. {pain.pain}: {pain.citation_url}")
    if not citation_lines:
        citation_lines.append("No external citations; pains marked as weak inference.")

    replacements = {
        "{{selected_demand_pocket}}": f"**{inp.demand_pocket}** (niche: {inp.niche})",
        "{{pain_rows}}": "\n".join(rows),
        "{{failed_alternatives}}": failed,
        "{{workarounds}}": workarounds,
        "{{emotional_triggers}}": emotional,
        "{{objections}}": "\n".join(objection_lines),
        "{{trust_barriers}}": trust,
        "{{compliance_risks}}": compliance,
        "{{messaging_angles}}": "\n".join(messaging_angles),
        "{{citations}}": "\n".join(citation_lines),
    }

    report = template
    for key, value in replacements.items():
        report = report.replace(key, value)
    return report


async def run_pain_mining_playbook(
    *,
    workspace_id: str,
    opportunity_id: str,
    request: PainMiningInput,
) -> str:
    try:
        read_artifact(opportunity_id, "01-market-demand.md")
    except FileNotFoundError:
        pass

    config = _DEPTH_CONFIG[request.research_depth]
    signals = await _gather_pain_signals(request)

    pains: list[MarketPain] = []
    for index, signal in enumerate(signals, start=1):
        pains.append(_pain_from_signal(signal, index=index))

    min_pains = config["min_pains"]
    while len(pains) < min_pains:
        pains.extend(_fallback_pains(request, min_pains - len(pains)))

    pains = rank_pains(pains[: max(min_pains, len(pains))])

    citation_issues = validate_pain_citations(pains)
    for pain in pains:
        if pain.pain in citation_issues:
            pain.evidence = "Moderate"
            pain.is_inference = True

    objections: list[str] = []
    for signal in signals:
        if _OBJECTION_WORDS.search(signal.snippet):
            objections.append(sanitize_quote(signal.snippet[:100], source=signal.source_kind))
    objections = objections[:8]

    messaging_angles = _messaging_angles(pains)

    for signal in signals:
        add_citation(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            url=signal.url,
            title=signal.title,
            snippet=signal.snippet,
            phase="pain_mining",
            artifact_filename="02-pain-mining.md",
            source=signal.source_kind,
        )

    report = _render_report(
        inp=request,
        pains=pains,
        signals=signals,
        objections=objections,
        messaging_angles=messaging_angles,
    )

    run_content_safety_checks(
        opportunity_id=opportunity_id,
        text=report,
        require_citations=bool(signals),
    )

    write_artifact(opportunity_id, "02-pain-mining.md", report)
    citations = [cite.model_dump(mode="json") for cite in list_citations(opportunity_id)]
    update_opportunity_json(
        opportunity_id,
        {
            "phase": "pain_mining",
            "status": "researching",
            "selected_demand_pocket": request.demand_pocket,
            "top_pains": [pain.model_dump() for pain in pains],
            "objections": objections,
            "messaging_angles": messaging_angles,
            "citations": citations,
        },
    )
    return report


def build_pain_mining_input_from_meta(meta: dict[str, Any]) -> PainMiningInput:
    depth = meta.get("research_depth", "standard")
    if depth not in {"quick", "standard", "deep"}:
        depth = "standard"
    return PainMiningInput(
        demand_pocket=_selected_demand_pocket(meta),
        niche=str(meta.get("niche") or meta.get("title") or "market"),
        icp_hints=meta.get("icp_hints") or meta.get("buyer_type"),
        banned_sources=list(meta.get("banned_sources") or []),
        research_depth=depth,
    )
