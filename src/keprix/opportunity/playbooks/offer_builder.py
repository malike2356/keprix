"""Offer Builder playbook for the Opportunity Engine."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from keprix.opportunity.approvals import request_approval
from keprix.opportunity.safety import run_content_safety_checks
from keprix.opportunity.workspace import read_artifact, read_opportunity_json, update_opportunity_json, write_artifact
from keprix.ui_contract import build_ui_contract

_FALSE_PROOF_RE = re.compile(
    r"\b(case study|customer achieved|clients earned|proven roi|guaranteed income|"
    r"guaranteed revenue|\d+%\s+increase for customer)\b",
    re.I,
)
_GUARANTEED_INCOME_RE = re.compile(
    r"\b(guaranteed income|guaranteed profit|get rich|financial freedom guaranteed)\b",
    re.I,
)
_REGULATED_RE = re.compile(
    r"\b(healthcare|medical|legal|financial services|fintech|insurance|hipaa|gdpr|"
    r"regulated|estate agent|solicitor|accountant)\b",
    re.I,
)


class OfferBuilderInput(BaseModel):
    niche: str
    title: str
    goal: str
    user_constraints: str = ""
    existing_assets: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)


class PricingHypothesis(BaseModel):
    tier: str
    price: str
    buyer_fit: str
    delivery_cost: str
    margin_risk: str
    notes: str


class OfferRecord(BaseModel):
    offer_name: str
    who_it_is_for: str
    pain_it_solves: list[str]
    core_promise: str
    unique_mechanism: str
    deliverables: list[str]
    included: list[str]
    excluded: list[str]
    proof_needed: list[str]
    guarantee_options: list[str]
    compliance_notes: list[str]
    implementation_requirements: list[str]
    sales_angle: str
    internal_notes: str


def detect_regulated_industry(text: str) -> bool:
    return bool(_REGULATED_RE.search(text))


def validate_no_false_proof(text: str, *, existing_assets: list[str]) -> list[str]:
    """Return violations when text claims proof without assets to support it."""
    if not _FALSE_PROOF_RE.search(text):
        return []
    if existing_assets:
        return []
    return ["Text references proof or outcomes without documented existing assets"]


def validate_no_guaranteed_income(text: str) -> list[str]:
    if _GUARANTEED_INCOME_RE.search(text):
        return ["Guaranteed income or profit language is not allowed"]
    return []


def _instance_capabilities() -> list[str]:
    contract = build_ui_contract()
    flags = contract.get("feature_flags", {})
    caps = [key for key, enabled in flags.items() if enabled]
    caps.extend(["research", "playbook_runtime", "workspace", "memory"])
    return sorted(set(caps))


def _load_top_pains(meta: dict[str, Any]) -> list[str]:
    pains = meta.get("top_pains") or []
    return [str(p.get("pain", "")) for p in pains[:5] if p.get("pain")]


def _read_optional_artifact(opportunity_id: str, filename: str) -> str:
    try:
        return read_artifact(opportunity_id, filename)
    except FileNotFoundError:
        return ""


def build_pricing_hypotheses(*, niche: str, buyer: str) -> list[PricingHypothesis]:
    return [
        PricingHypothesis(
            tier="Starter",
            price="$49/mo",
            buyer_fit=f"Solo operators in {niche}",
            delivery_cost="Low (automated research + templates)",
            margin_risk="Low",
            notes="Entry validation tier; limits deep research runs",
        ),
        PricingHypothesis(
            tier="Growth",
            price="$149/mo",
            buyer_fit=f"Small teams serving {buyer}",
            delivery_cost="Medium (playbook phases + assets)",
            margin_risk="Medium",
            notes="Includes offer, ICP, and launch assets",
        ),
        PricingHypothesis(
            tier="Scale",
            price="$499/mo",
            buyer_fit=f"Agencies or multi-offer operators in {niche}",
            delivery_cost="High (integrations + approval workflows)",
            margin_risk="Medium-High",
            notes="Custom integrations; human approval gates required",
        ),
        PricingHypothesis(
            tier="Pilot",
            price="$0 (paid pilot)",
            buyer_fit="Early design partners",
            delivery_cost="High touch",
            margin_risk="High",
            notes="Use for learning; not a long-term price anchor",
        ),
    ]


def build_offer_record(
    *,
    inp: OfferBuilderInput,
    pains: list[str],
    demand_pocket: str,
    regulated: bool,
) -> OfferRecord:
    primary_pain = pains[0] if pains else f"Operational friction in {inp.niche}"
    secondary = pains[1:4]
    offer_name = f"{inp.title} Validation Playbook"

    proof_needed = [
        "Customer interviews confirming top pains",
        "Pilot conversion metrics from pricing test",
    ]
    if inp.existing_assets:
        proof_needed.insert(0, f"Leverage existing assets: {', '.join(inp.existing_assets[:3])}")
    else:
        proof_needed.append("No existing case studies on file; do not claim customer outcomes")

    compliance = []
    if regulated:
        compliance.append("Regulated industry detected: add legal/compliance review before launch")
        compliance.append("Avoid medical, legal, or financial promises without licensed review")

    caps = inp.capabilities or _instance_capabilities()
    deliverables = [
        "Market demand report with ranked pockets",
        "Pain mining report mapped to offer",
        "Offer doc and pricing hypotheses",
        "ICP with disqualification criteria",
    ]
    if "governance" in caps:
        deliverables.append("Governance-backed research where policy allows")

    return OfferRecord(
        offer_name=offer_name,
        who_it_is_for=demand_pocket or f"Buyers in {inp.niche}",
        pain_it_solves=[primary_pain, *secondary],
        core_promise=f"Reduce {primary_pain.lower()} with a governed validation playbook",
        unique_mechanism="Phased opportunity playbooks with citation-backed research and approval gates",
        deliverables=deliverables,
        included=[
            "Research-backed demand and pain artifacts",
            "Structured offer and pricing drafts",
            "ICP and messaging angles",
        ],
        excluded=[
            "Done-for-you outbound without approval",
            "Guaranteed revenue outcomes",
            "Fabricated case studies",
        ],
        proof_needed=proof_needed,
        guarantee_options=[
            "Process guarantee: rerun research phase if citations missing",
            "No income or revenue guarantees",
        ],
        compliance_notes=compliance,
        implementation_requirements=[
            f"Capabilities available: {', '.join(caps[:8])}",
            "Human approval before ads, outreach, or CRM updates",
        ],
        sales_angle=f"Validate {inp.niche} opportunities faster than manual research",
        internal_notes=(
            f"Constraints: {inp.user_constraints or 'none'}. "
            "Do not publish proof claims until assets exist."
        ),
    )


def render_offer_doc(offer: OfferRecord) -> str:
    pains = "\n".join(f"- {pain}" for pain in offer.pain_it_solves)
    lines = [
        "# Offer Doc",
        "",
        "## Offer Name",
        offer.offer_name,
        "",
        "## Who It Is For",
        offer.who_it_is_for,
        "",
        "## Pain It Solves",
        pains,
        "",
        "## Core Promise",
        offer.core_promise,
        "",
        "## Unique Mechanism",
        offer.unique_mechanism,
        "",
        "## Deliverables",
        "\n".join(f"- {item}" for item in offer.deliverables),
        "",
        "## What Is Included",
        "\n".join(f"- {item}" for item in offer.included),
        "",
        "## What Is Not Included",
        "\n".join(f"- {item}" for item in offer.excluded),
        "",
        "## Proof Needed",
        "\n".join(f"- {item}" for item in offer.proof_needed),
        "",
        "## Guarantee Options",
        "\n".join(f"- {item}" for item in offer.guarantee_options),
        "",
        "## Risk And Compliance Notes",
        "\n".join(f"- {item}" for item in offer.compliance_notes) or "- None flagged",
        "",
        "## Implementation Requirements",
        "\n".join(f"- {item}" for item in offer.implementation_requirements),
        "",
        "## Sales Angle",
        offer.sales_angle,
        "",
        "## Internal Agent Notes",
        offer.internal_notes,
    ]
    return "\n".join(lines) + "\n"


def render_pricing_doc(hypotheses: list[PricingHypothesis], *, niche: str) -> str:
    rows = [
        "| Tier | Price | Buyer Fit | Delivery Cost | Margin Risk | Notes |",
        "| ---- | ----- | --------- | ------------- | ----------- | ----- |",
    ]
    for row in hypotheses:
        rows.append(
            f"| {row.tier} | {row.price} | {row.buyer_fit} | {row.delivery_cost} | "
            f"{row.margin_risk} | {row.notes} |",
        )
    body = [
        "# Pricing Strategy",
        "",
        "## Pricing Hypotheses",
        "",
        *rows,
        "",
        "## Competitor Price Anchors",
        f"- Research public pricing pages in {niche} before finalizing tiers",
        "- Anchor Growth tier against incumbent SaaS monthly plans",
        "",
        "## Labour Cost Comparison",
        "- Manual research + copywriting often exceeds Growth tier monthly cost",
        "- Scale tier should exceed cost of fractional operator time",
        "",
        "## Recommended Pricing Test",
        "- Run paid pilot tier with 3-5 design partners",
        "- Measure willingness to pay before locking annual plans",
        "",
        "## Risks",
        "- Underpricing Scale tier if integrations are required",
        "- Overpromising outcomes without proof assets",
    ]
    return "\n".join(body) + "\n"


def build_offer_builder_input_from_meta(meta: dict[str, Any]) -> OfferBuilderInput:
    return OfferBuilderInput(
        niche=str(meta.get("niche") or meta.get("title") or "market"),
        title=str(meta.get("title") or "Opportunity"),
        goal=str(meta.get("goal") or meta.get("title") or ""),
        user_constraints=str(meta.get("user_constraints") or ""),
        existing_assets=list(meta.get("existing_assets") or []),
        capabilities=list(meta.get("capabilities") or _instance_capabilities()),
    )


async def run_offer_builder_playbook(
    *,
    workspace_id: str,
    opportunity_id: str,
    request: OfferBuilderInput,
) -> tuple[str, str]:
    meta = read_opportunity_json(opportunity_id)
    market_demand = _read_optional_artifact(opportunity_id, "01-market-demand.md")
    pain_mining = _read_optional_artifact(opportunity_id, "02-pain-mining.md")
    pains = _load_top_pains(meta)
    if not pains and pain_mining:
        for line in pain_mining.splitlines():
            if line.startswith("|") and "|" in line[1:] and "Pain" not in line:
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if len(cells) >= 2:
                    pains.append(cells[1])
    demand_pocket = str(meta.get("recommended_demand_pocket") or meta.get("selected_demand_pocket") or "")

    combined_context = f"{request.niche} {market_demand[:500]} {pain_mining[:500]}"
    regulated = detect_regulated_industry(combined_context)

    offer = build_offer_record(
        inp=request,
        pains=pains,
        demand_pocket=demand_pocket,
        regulated=regulated,
    )
    hypotheses = build_pricing_hypotheses(niche=request.niche, buyer=offer.who_it_is_for)
    offer_doc = render_offer_doc(offer)
    pricing_doc = render_pricing_doc(hypotheses, niche=request.niche)

    violations = []
    violations.extend(validate_no_false_proof(offer_doc, existing_assets=request.existing_assets))
    violations.extend(validate_no_guaranteed_income(offer_doc + pricing_doc))
    if violations:
        offer.internal_notes += " GUARDRAIL: " + "; ".join(violations)

    run_content_safety_checks(opportunity_id=opportunity_id, text=offer_doc + pricing_doc)

    write_artifact(opportunity_id, "05-offer-doc.md", offer_doc)
    write_artifact(opportunity_id, "06-pricing.md", pricing_doc)

    update_opportunity_json(
        opportunity_id,
        {
            "phase": "offer_builder",
            "status": "validating",
            "offer": offer.model_dump(),
            "pricing": {"hypotheses": [row.model_dump() for row in hypotheses]},
            "offer_outline": {
                "promise": offer.core_promise,
                "mechanism": offer.unique_mechanism,
                "proof_points": offer.proof_needed,
            },
        },
    )
    return offer_doc, pricing_doc
