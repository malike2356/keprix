"""Validation Score playbook for the Opportunity Engine."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from keprix.opportunity.registry import get_opportunity_registry
from keprix.opportunity.safety import run_content_safety_checks
from keprix.opportunity.workspace import append_approval_log, read_artifact, read_opportunity_json, update_opportunity_json, write_artifact

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

SCORE_WEIGHTS: dict[str, int] = {
    "demand_strength": 15,
    "pain_urgency": 15,
    "icp_clarity": 10,
    "willingness_to_pay": 12,
    "competition_gap": 10,
    "offer_clarity": 12,
    "proof_readiness": 8,
    "delivery_feasibility": 8,
    "speed_to_launch": 5,
    "compliance_and_risk": 5,
}

Recommendation = Literal["Proceed", "Revise offer", "Gather more evidence", "Do not launch"]

_COMPLIANCE_RE = re.compile(
    r"\b(gdpr|hipaa|compliance|regulated|legal review|ethical|consent|risk)\b",
    re.I,
)
_PROOF_RE = re.compile(r"\b(case study|proof needed|customer achieved|testimonial)\b", re.I)
_INFERENCE_RE = re.compile(r"\b(weak inference|unverified|inferred)\b", re.I)


class ValidationScoreInput(BaseModel):
    user_override: bool = False
    override_reason: str = ""
    override_by: str = "system"


class CategoryScore(BaseModel):
    category: str
    label: str
    score: float
    weight: int
    evidence: str
    improvement: str


class ValidationResult(BaseModel):
    overall_score: float
    recommendation: Recommendation
    categories: list[CategoryScore]
    blocking_risks: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    approval_needed: list[str] = Field(default_factory=list)
    asset_generation_blocked: bool = False
    override_applied: bool = False


class ValidationBlockedError(Exception):
    """Raised when asset generation is blocked by validation score."""

    def __init__(self, result: ValidationResult) -> None:
        self.result = result
        super().__init__(
            f"Asset generation blocked: overall score {result.overall_score:.1f}, "
            f"recommendation={result.recommendation}",
        )


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, round(value, 1)))


def _read_optional(opportunity_id: str, filename: str) -> str:
    try:
        return read_artifact(opportunity_id, filename)
    except (FileNotFoundError, Exception):
        return ""


def _artifact_depth_score(text: str, *, min_good: int = 800) -> float:
    if not text or len(text.strip()) < 50:
        return 15.0
    length = len(text)
    score = 40.0 + min(40.0, length / 40.0)
    if _INFERENCE_RE.search(text):
        score -= 15.0
    if length >= min_good:
        score += 15.0
    return _clamp(score)


def compute_weighted_overall(categories: list[CategoryScore]) -> float:
    total_weight = sum(SCORE_WEIGHTS.values())
    weighted = sum(row.score * row.weight for row in categories)
    return _clamp(weighted / total_weight)


def recommendation_from_score(overall: float) -> Recommendation:
    if overall >= 80:
        return "Proceed"
    if overall >= 65:
        return "Revise offer"
    if overall >= 45:
        return "Gather more evidence"
    return "Do not launch"


def should_block_asset_generation(
    overall_score: float,
    *,
    user_override: bool = False,
) -> bool:
    if user_override:
        return False
    return overall_score < 65.0


def log_validation_override(
    *,
    opportunity_id: str,
    overall_score: float,
    recommendation: str,
    override_by: str,
    reason: str,
) -> None:
    registry = get_opportunity_registry()
    registry.append_event(
        opportunity_id,
        "validation.override",
        {
            "overall_score": overall_score,
            "recommendation": recommendation,
            "override_by": override_by,
            "reason": reason,
        },
    )
    append_approval_log(
        opportunity_id,
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "validation_override",
            "status": "approved",
            "actor": override_by,
        },
    )


def _score_categories(
    *,
    meta: dict[str, Any],
    artifacts: dict[str, str],
) -> tuple[list[CategoryScore], list[str], list[str]]:
    gaps: list[str] = []
    risks: list[str] = []

    demand_md = artifacts.get("01-market-demand.md", "")
    pain_md = artifacts.get("02-pain-mining.md", "")
    icp_md = artifacts.get("03-icp.md", "")
    comp_md = artifacts.get("04-competitors.md", "")
    offer_md = artifacts.get("05-offer-doc.md", "")
    pricing_md = artifacts.get("06-pricing.md", "")

    demand_pockets = meta.get("demand_pockets") or []
    top_pains = meta.get("top_pains") or []
    icp = meta.get("icp") or {}
    competitors = meta.get("competitors") or []
    offer = meta.get("offer") or {}
    pricing = meta.get("pricing", {}).get("hypotheses") or []

    market_label = str(meta.get("market") or "").strip().lower()
    niche_label = str(meta.get("niche") or "").strip().lower()
    weak_market = market_label in {"unknown", "n/a", "tbd"}
    weak_niche = "obscure" in niche_label or "no evidence" in niche_label

    if not demand_md:
        gaps.append("Missing market demand artifact")
    if not pain_md:
        gaps.append("Missing pain mining artifact")
    if not icp_md:
        gaps.append("Missing ICP artifact")

    demand_score = _artifact_depth_score(demand_md)
    if demand_pockets:
        demand_score = _clamp(demand_score + min(20.0, len(demand_pockets) * 2))
    if weak_market:
        gaps.append("Market not defined or unknown")
        demand_score = _clamp(demand_score - 30.0)
    if weak_niche:
        gaps.append("Niche lacks credible demand evidence")
        demand_score = _clamp(demand_score - 25.0)
        pain_score = _clamp(_artifact_depth_score(pain_md) - 20.0)
    else:
        pain_score = _artifact_depth_score(pain_md)
    if top_pains:
        urgent = sum(1 for p in top_pains if str(p.get("urgency", "")).lower() == "high")
        pain_score = _clamp(pain_score + urgent * 5)

    icp_score = _artifact_depth_score(icp_md)
    if icp.get("primary"):
        icp_score = _clamp(icp_score + 10)
    if len(icp.get("secondary") or []) >= 2:
        icp_score = _clamp(icp_score + 10)
    if "Disqualification" not in icp_md:
        gaps.append("ICP missing disqualification criteria")
        icp_score = _clamp(icp_score - 10)

    wtp_score = _artifact_depth_score(pricing_md)
    if len(pricing) >= 3:
        wtp_score = _clamp(wtp_score + 15)
    else:
        gaps.append("Fewer than 3 pricing hypotheses")

    gap_score = _artifact_depth_score(comp_md)
    if competitors:
        avg_gap = sum(float(c.get("differentiation_gap", 0)) for c in competitors) / len(competitors)
        gap_score = _clamp((gap_score + avg_gap) / 2)
    if "Unverified" in comp_md:
        risks.append("Competitor pricing largely unverified")

    offer_score = _artifact_depth_score(offer_md)
    if offer.get("core_promise"):
        offer_score = _clamp(offer_score + 10)
    if "## Pain It Solves" in offer_md:
        offer_score = _clamp(offer_score + 5)

    proof_score = 35.0
    proof_needed = offer.get("proof_needed") or []
    if proof_needed and not _PROOF_RE.search(offer_md):
        proof_score = 55.0
    if any("case study" in str(p).lower() for p in proof_needed):
        gaps.append("Proof assets not yet collected")
        proof_score = _clamp(proof_score - 10)
    if meta.get("existing_assets"):
        proof_score = _clamp(proof_score + 20)

    delivery_score = 50.0
    if offer.get("implementation_requirements"):
        delivery_score = 65.0
    completed = set(meta.get("completed_phases") or [])
    if {"offer_builder", "icp_builder", "competitor_intelligence"}.issubset(completed):
        delivery_score = _clamp(delivery_score + 15)

    speed_score = 45.0
    if completed:
        speed_score = _clamp(40.0 + len(completed) * 3)

    compliance_raw_risk = 30.0
    combined = f"{demand_md} {pain_md} {icp_md} {offer_md}"
    if _COMPLIANCE_RE.search(combined):
        compliance_raw_risk = 60.0
        risks.append("Compliance or regulated-industry signals present")
    compliance_score = _clamp(100.0 - compliance_raw_risk)

    categories = [
        CategoryScore(
            category="demand_strength",
            label="Demand strength",
            score=demand_score,
            weight=SCORE_WEIGHTS["demand_strength"],
            evidence="Market demand artifact depth and pocket count",
            improvement="Add cited demand pockets",
        ),
        CategoryScore(
            category="pain_urgency",
            label="Pain urgency",
            score=pain_score,
            weight=SCORE_WEIGHTS["pain_urgency"],
            evidence="Pain mining depth and high-urgency pains",
            improvement="Mine more pain evidence",
        ),
        CategoryScore(
            category="icp_clarity",
            label="ICP clarity",
            score=icp_score,
            weight=SCORE_WEIGHTS["icp_clarity"],
            evidence="ICP artifact and JSON structure",
            improvement="Sharpen primary ICP and disqualifiers",
        ),
        CategoryScore(
            category="willingness_to_pay",
            label="Willingness to pay",
            score=wtp_score,
            weight=SCORE_WEIGHTS["willingness_to_pay"],
            evidence="Pricing hypotheses count and detail",
            improvement="Add pricing tests",
        ),
        CategoryScore(
            category="competition_gap",
            label="Competition gap",
            score=gap_score,
            weight=SCORE_WEIGHTS["competition_gap"],
            evidence="Competitor differentiation scores",
            improvement="Strengthen differentiation narrative",
        ),
        CategoryScore(
            category="offer_clarity",
            label="Offer clarity",
            score=offer_score,
            weight=SCORE_WEIGHTS["offer_clarity"],
            evidence="Offer doc completeness",
            improvement="Clarify promise and mechanism",
        ),
        CategoryScore(
            category="proof_readiness",
            label="Proof readiness",
            score=proof_score,
            weight=SCORE_WEIGHTS["proof_readiness"],
            evidence="Proof needed vs assets on file",
            improvement="Collect proof before launch",
        ),
        CategoryScore(
            category="delivery_feasibility",
            label="Delivery feasibility",
            score=delivery_score,
            weight=SCORE_WEIGHTS["delivery_feasibility"],
            evidence="Implementation requirements and phases complete",
            improvement="Confirm delivery scope",
        ),
        CategoryScore(
            category="speed_to_launch",
            label="Speed to launch",
            score=speed_score,
            weight=SCORE_WEIGHTS["speed_to_launch"],
            evidence="Completed phases",
            improvement="Finish prerequisite phases",
        ),
        CategoryScore(
            category="compliance_and_risk",
            label="Compliance and risk",
            score=compliance_score,
            weight=SCORE_WEIGHTS["compliance_and_risk"],
            evidence="Inverted risk score from compliance signals",
            improvement="Complete compliance review",
        ),
    ]
    return categories, gaps, risks


def compute_validation_result(
    *,
    meta: dict[str, Any],
    artifacts: dict[str, str],
    user_override: bool = False,
) -> ValidationResult:
    categories, gaps, risks = _score_categories(meta=meta, artifacts=artifacts)
    overall = compute_weighted_overall(categories)
    market_label = str(meta.get("market") or "").strip().lower()
    niche_label = str(meta.get("niche") or "").strip().lower()
    if market_label in {"unknown", "n/a", "tbd"} or "obscure" in niche_label:
        overall = min(overall, 55.0)
        if "Weak opportunity profile" not in risks:
            risks.append("Weak opportunity profile: undefined market or unproven niche")
    recommendation = recommendation_from_score(overall)

    strengths = sorted(categories, key=lambda row: row.score, reverse=True)[:3]
    weak = sorted(categories, key=lambda row: row.score)[:3]

    improvements = [row.improvement for row in weak if row.score < 70]
    blocking = list(risks)
    if overall < 45:
        blocking.append("Overall score below minimum launch threshold")
    if recommendation == "Do not launch":
        blocking.append("Validation recommends do not launch")

    approval_needed: list[str] = []
    if should_block_asset_generation(overall, user_override=user_override):
        approval_needed.append("Validation score below 65: explicit override required for asset generation")
    if any(_COMPLIANCE_RE.search(a) for a in artifacts.values()):
        approval_needed.append("Compliance review before outbound or paid campaigns")

    return ValidationResult(
        overall_score=overall,
        recommendation=recommendation,
        categories=categories,
        blocking_risks=blocking,
        evidence_gaps=gaps,
        strengths=[f"{row.label}: {row.score:.0f}/100" for row in strengths],
        improvements=improvements,
        approval_needed=approval_needed,
        asset_generation_blocked=should_block_asset_generation(overall, user_override=user_override),
        override_applied=user_override,
    )


def render_validation_report(result: ValidationResult) -> str:
    template = (_TEMPLATES_DIR / "validation-score-report.md").read_text(encoding="utf-8")
    rows = []
    for row in result.categories:
        rows.append(
            f"| {row.label} | {row.score:.1f} | {row.weight} | {row.evidence} | {row.improvement} |",
        )
    replacements = {
        "{{overall_score}}": f"**{result.overall_score:.1f} / 100**",
        "{{recommendation}}": f"**{result.recommendation}**",
        "{{score_rows}}": "\n".join(rows),
        "{{strengths}}": "\n".join(f"- {s}" for s in result.strengths) or "- None identified",
        "{{risks}}": "\n".join(f"- {r}" for r in result.blocking_risks) or "- No critical risks flagged",
        "{{improvements}}": "\n".join(f"- {i}" for i in result.improvements) or "- Maintain current trajectory",
        "{{evidence_gaps}}": "\n".join(f"- {g}" for g in result.evidence_gaps) or "- No major gaps",
        "{{approval_needed}}": "\n".join(f"- {a}" for a in result.approval_needed) or "- None",
    }
    report = template
    for key, value in replacements.items():
        report = report.replace(key, value)
    if result.asset_generation_blocked:
        report += "\n> Asset generation is blocked until score improves or override is logged.\n"
    return report


def can_proceed_to_assets(opportunity_id: str, *, user_override: bool = False) -> tuple[bool, ValidationResult | None]:
    meta = read_opportunity_json(opportunity_id)
    validation = meta.get("validation") or {}
    if user_override or validation.get("override_applied"):
        return True, None
    overall = float(validation.get("overall_score", 0))
    if overall >= 65:
        return True, None
    artifacts = {
        name: _read_optional(opportunity_id, name)
        for name in (
            "01-market-demand.md",
            "02-pain-mining.md",
            "03-icp.md",
            "04-competitors.md",
            "05-offer-doc.md",
            "06-pricing.md",
        )
    }
    result = compute_validation_result(meta=meta, artifacts=artifacts, user_override=False)
    return not result.asset_generation_blocked, result


async def run_validation_score_playbook(
    *,
    workspace_id: str,
    opportunity_id: str,
    request: ValidationScoreInput | None = None,
) -> str:
    req = request or ValidationScoreInput()
    meta = read_opportunity_json(opportunity_id)
    artifacts = {
        filename: _read_optional(opportunity_id, filename)
        for filename in (
            "01-market-demand.md",
            "02-pain-mining.md",
            "03-icp.md",
            "04-competitors.md",
            "05-offer-doc.md",
            "06-pricing.md",
        )
    }

    result = compute_validation_result(
        meta=meta,
        artifacts=artifacts,
        user_override=req.user_override,
    )

    if req.user_override:
        log_validation_override(
            opportunity_id=opportunity_id,
            overall_score=result.overall_score,
            recommendation=result.recommendation,
            override_by=req.override_by,
            reason=req.override_reason or "User explicitly overrode validation threshold",
        )
        result.override_applied = True
        result.asset_generation_blocked = False

    report = render_validation_report(result)
    run_content_safety_checks(opportunity_id=opportunity_id, text=report)

    write_artifact(opportunity_id, "12-validation-score.md", report)
    update_opportunity_json(
        opportunity_id,
        {
            "phase": "validation_score",
            "status": "validating",
            "validation": {
                "overall_score": result.overall_score,
                "recommendation": result.recommendation,
                "blocking_risks": result.blocking_risks,
                "evidence_gaps": result.evidence_gaps,
                "asset_generation_blocked": result.asset_generation_blocked,
                "override_applied": result.override_applied,
                "categories": [row.model_dump() for row in result.categories],
            },
            "scores": {
                "overall": result.overall_score,
                "recommendation": result.recommendation,
            },
        },
    )
    return report
