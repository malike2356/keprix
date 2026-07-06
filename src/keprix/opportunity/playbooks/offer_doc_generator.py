"""Canonical Offer Doc and Agent Memory playbook."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from keprix.opportunity.safety import run_content_safety_checks
from keprix.opportunity.workspace import read_artifact, read_opportunity_json, update_opportunity_json, write_artifact

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_MEMORY_BRIEF_MAX_CHARS = 2500


class CanonicalOfferDoc(BaseModel):
    offer_name: str
    positioning: str
    target_market: str
    primary_icp: str
    core_pain: str
    core_promise: str
    unique_mechanism: str
    deliverables: list[str] = Field(default_factory=list)
    pricing_summary: str = ""
    guarantee: str = ""
    proof_needed: list[str] = Field(default_factory=list)
    competitor_positioning: str = ""
    differentiation: str = ""
    funnel_strategy: str = ""
    content_strategy: str = ""
    outreach_strategy: str = ""
    compliance_notes: list[str] = Field(default_factory=list)
    words_to_use: list[str] = Field(default_factory=list)
    words_to_avoid: list[str] = Field(default_factory=list)
    claims_allowed: list[str] = Field(default_factory=list)
    claims_forbidden: list[str] = Field(default_factory=list)
    approval_rules: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    validation_score: float | None = None
    validation_recommendation: str = ""


def memory_enabled() -> bool:
    try:
        from keprix.ui_contract import build_ui_contract

        flags = build_ui_contract().get("feature_flags", {})
        return bool(flags.get("data_workspace", True))
    except Exception:
        return True


def _read_optional(opportunity_id: str, filename: str) -> str:
    try:
        return read_artifact(opportunity_id, filename)
    except (FileNotFoundError, Exception):
        return ""


def load_canonical_offer_doc(opportunity_id: str) -> str:
    """Load canonical offer doc for downstream playbooks."""
    content = _read_optional(opportunity_id, "05-offer-doc.md")
    if not content.strip():
        raise FileNotFoundError(f"Canonical offer doc missing for {opportunity_id}")
    return content


def load_agent_memory_brief(opportunity_id: str) -> str:
    content = _read_optional(opportunity_id, "agent-memory-brief.md")
    if not content.strip():
        raise FileNotFoundError(f"Agent memory brief missing for {opportunity_id}")
    return content


def _list_lines(items: list[str], *, bullet: bool = True) -> str:
    if not items:
        return "- None documented"
    if bullet:
        return "\n".join(f"- {item}" for item in items)
    return "\n".join(items)


def build_canonical_offer_from_meta(meta: dict[str, Any]) -> CanonicalOfferDoc:
    offer = meta.get("offer") or {}
    icp = meta.get("icp") or {}
    validation = meta.get("validation") or {}
    competitors = meta.get("competitors") or []
    pricing_rows = meta.get("pricing", {}).get("hypotheses") or []
    pains = [str(p.get("pain", "")) for p in meta.get("top_pains", [])[:3] if p.get("pain")]
    messaging = list(meta.get("messaging_angles") or [])[:3]

    offer_name = str(offer.get("offer_name") or meta.get("title") or "Opportunity Offer")
    niche = str(meta.get("niche") or meta.get("market") or "target market")
    primary_icp = str((icp.get("primary") or {}).get("summary") or meta.get("recommended_demand_pocket") or niche)
    core_pain = pains[0] if pains else f"Operational friction in {niche}"
    core_promise = str(offer.get("core_promise") or f"Help {primary_icp} solve {core_pain.lower()}")
    mechanism = str(offer.get("unique_mechanism") or "Governed validation playbooks with approval gates")

    pricing_summary = "\n".join(
        f"- {row.get('tier', 'Tier')}: {row.get('price', 'TBD')}" for row in pricing_rows[:4]
    ) or "- Pricing hypotheses pending"

    competitor_positioning = "Competitive landscape documented in 04-competitors.md"
    if competitors:
        names = [str(c.get("name", "")) for c in competitors[:5] if c.get("name")]
        competitor_positioning = "Key competitors: " + ", ".join(names)

    differentiation = str(meta.get("differentiation_recommendation") or offer.get("sales_angle") or "")
    validation_score = validation.get("overall_score")
    validation_rec = str(validation.get("recommendation") or "")
    if validation_score is None:
        validation_rec = validation_rec or "Validation score not yet computed; gather evidence before launch"
        open_questions = ["Run validation score playbook before asset generation"]
    else:
        open_questions = list(validation.get("evidence_gaps") or [])[:5]

    claims_allowed = [
        "Research-backed market and pain findings with citations",
        "Process-oriented guarantees (rerun research, structured validation)",
        "Pricing hypotheses subject to pilot testing",
    ]
    claims_forbidden = [
        "Guaranteed income or revenue outcomes",
        "Fabricated case studies or customer results",
        "Medical, legal, or financial promises without review",
        "Deceptive competitor comparisons or false endorsements",
    ]
    if not meta.get("existing_assets"):
        claims_forbidden.append("Any customer outcome claims without proof assets on file")

    approval_rules = [
        "Explicit approval before ads, outreach, CRM updates, or spending money",
        "Explicit approval before publishing landing pages or email sequences",
    ]
    if validation_score is not None and float(validation_score) < 65:
        approval_rules.append("Validation score below 65: override required before asset generation")

    compliance_notes = list(offer.get("compliance_notes") or [])
    gaps = validation.get("blocking_risks") or []
    compliance_notes.extend(str(g) for g in gaps[:3])

    return CanonicalOfferDoc(
        offer_name=offer_name,
        positioning=f"{offer_name}: {core_promise}",
        target_market=niche,
        primary_icp=primary_icp,
        core_pain=core_pain,
        core_promise=core_promise,
        unique_mechanism=mechanism,
        deliverables=list(offer.get("deliverables") or ["Validation playbook artifacts"]),
        pricing_summary=pricing_summary,
        guarantee=_list_lines(list(offer.get("guarantee_options") or ["No income guarantees"]), bullet=False),
        proof_needed=list(offer.get("proof_needed") or ["Customer interviews", "Pilot conversion metrics"]),
        competitor_positioning=competitor_positioning,
        differentiation=differentiation or "Speed-to-validation with governed execution",
        funnel_strategy="Awareness content > validation score > offer review call",
        content_strategy=_list_lines(messaging or [f"Educational content on pains in {niche}"], bullet=False),
        outreach_strategy="Warm outreach only after ICP approval gate; no bulk cold outreach without review",
        compliance_notes=compliance_notes,
        words_to_use=["validate", "evidence", "playbook", "approval", "pilot"],
        words_to_avoid=["guaranteed", "get rich", "false identity", "hack", "secret"],
        claims_allowed=claims_allowed,
        claims_forbidden=claims_forbidden,
        approval_rules=approval_rules,
        open_questions=open_questions,
        validation_score=float(validation_score) if validation_score is not None else None,
        validation_recommendation=validation_rec,
    )


def render_canonical_offer_doc(doc: CanonicalOfferDoc) -> str:
    template = (_TEMPLATES_DIR / "canonical-offer-doc.md").read_text(encoding="utf-8")
    validation_line = (
        f"{doc.validation_score:.1f}/100 ({doc.validation_recommendation})"
        if doc.validation_score is not None
        else f"Not available ({doc.validation_recommendation})"
    )
    replacements = {
        "{{offer_name}}": doc.offer_name,
        "{{positioning}}": doc.positioning,
        "{{target_market}}": doc.target_market,
        "{{primary_icp}}": doc.primary_icp,
        "{{core_pain}}": doc.core_pain,
        "{{core_promise}}": doc.core_promise,
        "{{unique_mechanism}}": doc.unique_mechanism,
        "{{deliverables}}": _list_lines(doc.deliverables),
        "{{pricing}}": doc.pricing_summary,
        "{{guarantee}}": doc.guarantee,
        "{{proof_needed}}": _list_lines(doc.proof_needed),
        "{{competitor_positioning}}": doc.competitor_positioning,
        "{{differentiation}}": doc.differentiation,
        "{{funnel_strategy}}": doc.funnel_strategy,
        "{{content_strategy}}": doc.content_strategy,
        "{{outreach_strategy}}": doc.outreach_strategy,
        "{{compliance_notes}}": _list_lines(doc.compliance_notes),
        "{{words_to_use}}": _list_lines(doc.words_to_use),
        "{{words_to_avoid}}": _list_lines(doc.words_to_avoid),
        "{{claims_allowed}}": _list_lines(doc.claims_allowed),
        "{{claims_forbidden}}": _list_lines(doc.claims_forbidden),
        "{{approval_rules}}": _list_lines(doc.approval_rules),
        "{{open_questions}}": _list_lines(doc.open_questions),
    }
    body = template
    for key, value in replacements.items():
        body = body.replace(key, value)
    header = (
        "# Canonical Offer Doc\n\n"
        f"Validation score: {validation_line}\n\n"
    )
    return header + body


def render_agent_memory_brief(*, opportunity_name: str, doc: CanonicalOfferDoc) -> str:
    template = (_TEMPLATES_DIR / "agent-memory-brief.md").read_text(encoding="utf-8")
    pains = _list_lines([doc.core_pain] + (doc.open_questions[:2] if doc.open_questions else []))
    replacements = {
        "{{opportunity_name}}": opportunity_name,
        "{{positioning}}": doc.positioning[:300],
        "{{icp}}": doc.primary_icp[:300],
        "{{pains}}": pains[:500],
        "{{mechanism}}": doc.unique_mechanism[:300],
        "{{forbidden_claims}}": _list_lines(doc.claims_forbidden)[:800],
        "{{approval_before}}": _list_lines(doc.approval_rules)[:600],
    }
    brief = template
    for key, value in replacements.items():
        brief = brief.replace(key, value)
    if len(brief) > _MEMORY_BRIEF_MAX_CHARS:
        brief = brief[: _MEMORY_BRIEF_MAX_CHARS - 20].rstrip() + "\n\n(truncated)\n"
    return brief


async def store_opportunity_scoped_memory(
    *,
    workspace_id: str,
    opportunity_id: str,
    brief: str,
    user_id: str = "local",
) -> str | None:
    if not memory_enabled():
        return None
    try:
        from keprix.memory.episodic.store import create_episodic_store

        store = create_episodic_store()
        memory_id = await store.save(
            user_id,
            brief,
            metadata={
                "tags": ["opportunity", "offer", "icp", "launch"],
                "opportunity_id": opportunity_id,
                "workspace_id": workspace_id,
                "scope": "opportunity",
                "source": "offer_doc_generator",
            },
        )
        return memory_id
    except Exception:
        return None


async def run_offer_doc_generator_playbook(
    *,
    workspace_id: str,
    opportunity_id: str,
    user_id: str = "local",
) -> tuple[str, str]:
    meta = read_opportunity_json(opportunity_id)
    _read_optional(opportunity_id, "01-market-demand.md")
    _read_optional(opportunity_id, "02-pain-mining.md")
    _read_optional(opportunity_id, "03-icp.md")
    _read_optional(opportunity_id, "04-competitors.md")
    pricing_md = _read_optional(opportunity_id, "06-pricing.md")
    _read_optional(opportunity_id, "12-validation-score.md")

    doc = build_canonical_offer_from_meta(meta)
    canonical_md = render_canonical_offer_doc(doc)
    memory_brief = render_agent_memory_brief(
        opportunity_name=str(meta.get("title") or opportunity_id),
        doc=doc,
    )

    run_content_safety_checks(opportunity_id=opportunity_id, text=canonical_md + memory_brief)

    write_artifact(opportunity_id, "05-offer-doc.md", canonical_md)
    write_artifact(opportunity_id, "agent-memory-brief.md", memory_brief)

    memory_id = await store_opportunity_scoped_memory(
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        brief=memory_brief,
        user_id=user_id,
    )

    update_opportunity_json(
        opportunity_id,
        {
            "phase": "offer_doc",
            "canonical_offer": doc.model_dump(),
            "claims_allowed": doc.claims_allowed,
            "claims_forbidden": doc.claims_forbidden,
            "agent_memory_brief_path": "agent-memory-brief.md",
            "agent_memory_id": memory_id,
        },
    )

    if not pricing_md.strip():
        pricing_md = "# Pricing Strategy\n\nSee canonical offer doc pricing section.\n"

    return canonical_md, pricing_md
