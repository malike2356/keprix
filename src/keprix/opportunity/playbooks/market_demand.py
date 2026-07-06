"""Market Demand Discovery playbook for the Opportunity Engine."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from keprix.opportunity.citations import add_citation, list_citations
from keprix.opportunity.safety import SafetyViolation, run_content_safety_checks, validate_research_url
from keprix.opportunity.workspace import read_opportunity_json, update_opportunity_json, write_artifact
from keprix.research.search import web_search

ResearchDepth = Literal["quick", "standard", "deep"]

SCORE_WEIGHTS = {
    "urgency": 30,
    "evidence": 25,
    "willingness_to_pay": 25,
    "competition_gap": 20,
}

_DEPTH_CONFIG: dict[ResearchDepth, dict[str, int]] = {
    "quick": {"queries": 3, "results_per_query": 3, "min_pockets": 3},
    "standard": {"queries": 5, "results_per_query": 5, "min_pockets": 5},
    "deep": {"queries": 8, "results_per_query": 5, "min_pockets": 5},
}

_URGENCY_WORDS = re.compile(r"\b(urgent|urgently|now|immediate|growing|shortage|deadline)\b", re.I)
_WTP_WORDS = re.compile(r"\b(pay|budget|pricing|subscription|spend|procurement|purchase)\b", re.I)
_GAP_WORDS = re.compile(r"\b(gap|missing|lack|no solution|underserved|unmet|fragmented)\b", re.I)
_QUESTION_WORDS = re.compile(r"\b(how|what|why|when|where|can i|should i)\b", re.I)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class MarketDemandInput(BaseModel):
    niche: str = Field(..., min_length=1)
    geography: str | None = None
    buyer_type: str | None = None
    budget_range: str | None = None
    exclusions: list[str] = Field(default_factory=list)
    research_depth: ResearchDepth = "standard"

    @field_validator("niche")
    @classmethod
    def strip_niche(cls, value: str) -> str:
        return value.strip()


class DemandPocket(BaseModel):
    rank: int
    name: str
    buyer: str
    pain: str
    urgency_score: float
    evidence_score: float
    willingness_to_pay_score: float
    competition_gap_score: float
    overall_demand_score: float
    evidence_strength: str
    monetisation_potential: str
    citation_urls: list[str] = Field(default_factory=list)
    inference_note: str = ""


@dataclass
class ResearchSignal:
    title: str
    url: str
    snippet: str
    source_kind: str
    from_workspace: bool = False


def compute_overall_demand_score(
    *,
    urgency_score: float,
    evidence_score: float,
    willingness_to_pay_score: float,
    competition_gap_score: float,
) -> float:
    total = (
        urgency_score * SCORE_WEIGHTS["urgency"]
        + evidence_score * SCORE_WEIGHTS["evidence"]
        + willingness_to_pay_score * SCORE_WEIGHTS["willingness_to_pay"]
        + competition_gap_score * SCORE_WEIGHTS["competition_gap"]
    )
    return round(total / sum(SCORE_WEIGHTS.values()), 1)


def evidence_strength_label(evidence_score: float, citation_count: int) -> str:
    if evidence_score >= 70 and citation_count >= 1:
        return "Strong"
    if evidence_score >= 40:
        return "Moderate"
    return "Weak inference"


def monetisation_label(willingness_score: float) -> str:
    if willingness_score >= 70:
        return "High"
    if willingness_score >= 45:
        return "Medium"
    return "Low"


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 1)))


def _score_signal(signal: ResearchSignal) -> dict[str, float]:
    text = f"{signal.title} {signal.snippet}".lower()
    urgency = 35.0 + (15.0 if _URGENCY_WORDS.search(text) else 0.0)
    wtp = 30.0 + (20.0 if _WTP_WORDS.search(text) else 0.0)
    gap = 35.0 + (20.0 if _GAP_WORDS.search(text) else 0.0)
    evidence = 55.0 if not signal.from_workspace else 45.0
    if signal.url and not signal.from_workspace:
        evidence += 15.0
    if len(signal.snippet) > 120:
        evidence += 10.0
    return {
        "urgency_score": _clamp_score(urgency),
        "evidence_score": _clamp_score(evidence),
        "willingness_to_pay_score": _clamp_score(wtp),
        "competition_gap_score": _clamp_score(gap),
    }


def _search_queries(inp: MarketDemandInput) -> list[tuple[str, str]]:
    geo = f" {inp.geography}" if inp.geography else ""
    buyer = inp.buyer_type or "buyers"
    base = inp.niche
    queries: list[tuple[str, str]] = [
        (f"{base}{geo} market demand trends", "web_search"),
        (f"{base}{geo} {buyer} pain points forum", "forums"),
        (f"{base}{geo} jobs hiring skills demand", "job_boards"),
        (f"{base}{geo} software reviews marketplace", "reviews"),
        (f"{base}{geo} competitors pricing landing pages", "competitors"),
        (f"{base}{geo} buying triggers procurement", "spend_signals"),
        (f"{base}{geo} reddit questions problems", "social"),
        (f"{base}{geo} ad library examples", "ads"),
    ]
    if inp.exclusions:
        excl = " ".join(f"-{term}" for term in inp.exclusions[:3])
        queries = [(f"{q} {excl}", kind) for q, kind in queries]
    limit = _DEPTH_CONFIG[inp.research_depth]["queries"]
    return queries[:limit]


async def _gather_workspace_knowledge(
    *,
    workspace_id: str,
    user_id: str,
    query: str,
    limit: int = 5,
) -> list[ResearchSignal]:
    signals: list[ResearchSignal] = []
    try:
        from keprix.memory.rag.retriever import RagRetriever

        retriever = RagRetriever()
        rows = await retriever.hybrid_search(user_id or workspace_id, query, limit=limit)
        for row in rows:
            content = str(row.get("content", "")).strip()
            if not content:
                continue
            source = str(row.get("source", "workspace"))
            signals.append(
                ResearchSignal(
                    title=f"Workspace knowledge: {source}",
                    url=f"workspace://{workspace_id}/{source}",
                    snippet=content[:500],
                    source_kind="workspace",
                    from_workspace=True,
                ),
            )
    except Exception:
        pass
    return signals


async def _gather_web_signals(
    inp: MarketDemandInput,
    *,
    results_per_query: int,
) -> list[ResearchSignal]:
    signals: list[ResearchSignal] = []
    seen_urls: set[str] = set()
    for query, kind in _search_queries(inp):
        results = await web_search(query, limit=results_per_query)
        for item in results:
            url = str(item.get("url", "")).strip()
            if not url or url in seen_urls:
                continue
            try:
                validate_research_url(url)
            except SafetyViolation:
                continue
            seen_urls.add(url)
            signals.append(
                ResearchSignal(
                    title=str(item.get("title", "")),
                    url=url,
                    snippet=str(item.get("snippet", "")),
                    source_kind=kind,
                ),
            )
    return signals


def _pocket_name_from_signal(signal: ResearchSignal, index: int) -> str:
    title = signal.title.strip()
    if len(title) > 60:
        title = title[:57] + "..."
    if title:
        return title
    return f"Demand pocket {index}"


def _build_demand_pockets(
    signals: list[ResearchSignal],
    *,
    inp: MarketDemandInput,
) -> list[DemandPocket]:
    min_pockets = _DEPTH_CONFIG[inp.research_depth]["min_pockets"]
    buyer_default = inp.buyer_type or "Target buyers in niche"

    pockets: list[DemandPocket] = []
    for index, signal in enumerate(signals[: max(min_pockets, len(signals))], start=1):
        scores = _score_signal(signal)
        citation_urls = [] if signal.from_workspace else ([signal.url] if signal.url else [])
        evidence_score = scores["evidence_score"]
        strength = evidence_strength_label(evidence_score, len(citation_urls))
        inference_note = ""
        if strength == "Weak inference":
            inference_note = "Based on limited public signals; validate before committing."

        pocket = DemandPocket(
            rank=index,
            name=_pocket_name_from_signal(signal, index),
            buyer=buyer_default,
            pain=signal.snippet[:240] or "Pain inferred from public discussion.",
            urgency_score=scores["urgency_score"],
            evidence_score=evidence_score,
            willingness_to_pay_score=scores["willingness_to_pay_score"],
            competition_gap_score=scores["competition_gap_score"],
            overall_demand_score=compute_overall_demand_score(**scores),
            evidence_strength=strength,
            monetisation_potential=monetisation_label(scores["willingness_to_pay_score"]),
            citation_urls=citation_urls,
            inference_note=inference_note,
        )
        pockets.append(pocket)

    while len(pockets) < min_pockets:
        idx = len(pockets) + 1
        scores = {
            "urgency_score": 25.0,
            "evidence_score": 20.0,
            "willingness_to_pay_score": 25.0,
            "competition_gap_score": 30.0,
        }
        pockets.append(
            DemandPocket(
                rank=idx,
                name=f"Exploratory pocket: {inp.niche} segment {idx}",
                buyer=buyer_default,
                pain="Weak inference: additional research needed to confirm pain.",
                urgency_score=scores["urgency_score"],
                evidence_score=scores["evidence_score"],
                willingness_to_pay_score=scores["willingness_to_pay_score"],
                competition_gap_score=scores["competition_gap_score"],
                overall_demand_score=compute_overall_demand_score(**scores),
                evidence_strength="Weak inference",
                monetisation_potential="Low",
                citation_urls=[],
                inference_note="Fallback pocket generated because public search returned limited signals.",
            ),
        )

    pockets.sort(key=lambda row: row.overall_demand_score, reverse=True)
    for rank, pocket in enumerate(pockets, start=1):
        pocket.rank = rank
    return pockets


def _empty_search_fallback_pockets(inp: MarketDemandInput) -> list[DemandPocket]:
    min_pockets = _DEPTH_CONFIG[inp.research_depth]["min_pockets"]
    buyer = inp.buyer_type or "Target buyers"
    pockets: list[DemandPocket] = []
    for idx in range(1, min_pockets + 1):
        scores = {
            "urgency_score": 22.0,
            "evidence_score": 15.0,
            "willingness_to_pay_score": 20.0,
            "competition_gap_score": 28.0,
        }
        pockets.append(
            DemandPocket(
                rank=idx,
                name=f"Unverified demand angle {idx} in {inp.niche}",
                buyer=buyer,
                pain="No public search results returned; treat as hypothesis only.",
                urgency_score=scores["urgency_score"],
                evidence_score=scores["evidence_score"],
                willingness_to_pay_score=scores["willingness_to_pay_score"],
                competition_gap_score=scores["competition_gap_score"],
                overall_demand_score=compute_overall_demand_score(**scores),
                evidence_strength="Weak inference",
                monetisation_potential="Low",
                citation_urls=[],
                inference_note="Empty-search fallback; rerun with deeper research or alternate sources.",
            ),
        )
    return pockets


def validate_pockets_have_citations(pockets: list[DemandPocket]) -> list[str]:
    """Return pocket names that claim strong evidence without citations."""
    issues: list[str] = []
    for pocket in pockets:
        if pocket.evidence_strength == "Strong" and not pocket.citation_urls:
            issues.append(pocket.name)
    return issues


def _render_search_brief(inp: MarketDemandInput, *, title: str, goal: str) -> str:
    lines = [
        f"- **Opportunity title:** {title}",
        f"- **Niche:** {inp.niche}",
        f"- **Goal:** {goal}",
        f"- **Research depth:** {inp.research_depth}",
    ]
    if inp.geography:
        lines.append(f"- **Geography:** {inp.geography}")
    if inp.buyer_type:
        lines.append(f"- **Buyer type:** {inp.buyer_type}")
    if inp.budget_range:
        lines.append(f"- **Budget range:** {inp.budget_range}")
    if inp.exclusions:
        lines.append(f"- **Exclusions:** {', '.join(inp.exclusions)}")
    return "\n".join(lines)


def _render_report(
    *,
    inp: MarketDemandInput,
    title: str,
    goal: str,
    pockets: list[DemandPocket],
    signals: list[ResearchSignal],
    recommended: DemandPocket,
) -> str:
    template_path = _TEMPLATES_DIR / "market-demand-report.md"
    template = template_path.read_text(encoding="utf-8")

    rows: list[str] = []
    for pocket in pockets:
        rows.append(
            "| {rank} | {name} | {buyer} | {pain} | {urgency:.0f} | {strength} | {money} |".format(
                rank=pocket.rank,
                name=pocket.name.replace("|", "/"),
                buyer=pocket.buyer.replace("|", "/"),
                pain=pocket.pain.replace("|", "/")[:80],
                urgency=pocket.urgency_score,
                strength=pocket.evidence_strength,
                money=pocket.monetisation_potential,
            ),
        )

    signal_lines = []
    for signal in signals[:20]:
        label = "workspace" if signal.from_workspace else signal.source_kind
        signal_lines.append(f"- [{signal.title}]({signal.url}) ({label})")
        if signal.snippet:
            signal_lines.append(f"  - {signal.snippet[:200]}")

    questions = []
    for signal in signals:
        if _QUESTION_WORDS.search(signal.snippet or signal.title):
            questions.append(f"- {signal.snippet[:160] or signal.title}")
    if not questions:
        questions.append("- No repeated questions surfaced; expand forum and social queries.")

    buying_triggers = [
        "- Regulatory or compliance deadline mentioned in niche discussions",
        "- Team capacity constraints and manual workflow fatigue",
        "- Visible competitor spend on ads or hiring in the niche",
    ]
    spend_signals = [
        "- Job postings requiring niche skills",
        "- Paid software categories with active review activity",
        "- Marketplace listings with recurring subscription pricing",
    ]
    gaps = [
        "- Fragmented tooling without an integrated workflow",
        "- Long onboarding or services-heavy incumbent offers",
        "- Limited solutions tailored to the stated buyer type",
    ]
    risks = [
        "- Weak evidence pockets require validation before offer design",
        "- Competitive incumbents may compress willingness to pay",
        "- Geography or budget constraints may shrink addressable demand",
    ]

    citation_lines = []
    cite_index = 1
    for pocket in pockets:
        for url in pocket.citation_urls:
            citation_lines.append(f"{cite_index}. {pocket.name}: {url}")
            cite_index += 1
    if not citation_lines:
        citation_lines.append("No external citations captured; all pockets are weak inference.")

    recommended_text = (
        f"**{recommended.name}** (overall score {recommended.overall_demand_score:.1f}/100)\n\n"
        f"Justification: highest weighted demand score with {recommended.evidence_strength.lower()} "
        f"evidence and {recommended.monetisation_potential.lower()} monetisation potential. "
        f"{recommended.inference_note}"
    )

    replacements = {
        "{{search_brief}}": _render_search_brief(inp, title=title, goal=goal),
        "{{demand_pocket_rows}}": "\n".join(rows),
        "{{signals_found}}": "\n".join(signal_lines) or "- No signals returned from search.",
        "{{repeated_questions}}": "\n".join(questions[:8]),
        "{{buying_triggers}}": "\n".join(buying_triggers),
        "{{existing_spend_signals}}": "\n".join(spend_signals),
        "{{solution_gaps}}": "\n".join(gaps),
        "{{market_risks}}": "\n".join(risks),
        "{{recommended_opportunity}}": recommended_text,
        "{{citations}}": "\n".join(citation_lines),
    }

    report = template
    for key, value in replacements.items():
        report = report.replace(key, value)
    return report


async def run_market_demand_playbook(
    *,
    workspace_id: str,
    opportunity_id: str,
    request: MarketDemandInput,
    title: str,
    goal: str,
    user_id: str = "local",
) -> str:
    config = _DEPTH_CONFIG[request.research_depth]
    workspace_signals = await _gather_workspace_knowledge(
        workspace_id=workspace_id,
        user_id=user_id,
        query=request.niche,
        limit=config["results_per_query"],
    )
    web_signals = await _gather_web_signals(
        request,
        results_per_query=config["results_per_query"],
    )
    signals = workspace_signals + web_signals

    if not web_signals and not workspace_signals:
        pockets = _empty_search_fallback_pockets(request)
    else:
        combined = signals if signals else web_signals
        pockets = _build_demand_pockets(combined, inp=request)

    citation_issues = validate_pockets_have_citations(pockets)
    if citation_issues:
        for pocket in pockets:
            if pocket.name in citation_issues:
                pocket.evidence_strength = "Moderate"
                pocket.inference_note = "Downgraded: strong label removed due to missing citations."

    for signal in web_signals:
        if signal.url.startswith("workspace://"):
            continue
        add_citation(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            url=signal.url,
            title=signal.title,
            snippet=signal.snippet,
            phase="market_demand",
            artifact_filename="01-market-demand.md",
            source=signal.source_kind,
        )

    recommended = pockets[0]
    report = _render_report(
        inp=request,
        title=title,
        goal=goal,
        pockets=pockets,
        signals=signals,
        recommended=recommended,
    )

    run_content_safety_checks(
        opportunity_id=opportunity_id,
        text=report,
        require_citations=bool(web_signals),
    )

    write_artifact(opportunity_id, "01-market-demand.md", report)
    citations = [cite.model_dump(mode="json") for cite in list_citations(opportunity_id)]
    update_opportunity_json(
        opportunity_id,
        {
            "phase": "market_demand",
            "status": "researching",
            "demand_pockets": [pocket.model_dump() for pocket in pockets],
            "recommended_demand_pocket": recommended.name,
            "citations": citations,
        },
    )
    return report
