"""Validation scoring for opportunity workspaces."""

from __future__ import annotations

from datetime import datetime, timezone

from keprix.opportunity.models import OpportunityPhase, OpportunityScore
from keprix.opportunity.playbooks.validation_score import (
    ValidationScoreInput,
    compute_validation_result,
    compute_weighted_overall,
    recommendation_from_score,
    render_validation_report,
    run_validation_score_playbook,
)
from keprix.opportunity.workspace import read_artifact, read_opportunity_json, update_opportunity_json


def compute_validation_score(
    *,
    workspace_id: str,
    opportunity_id: str,
    source: str = "scoring",
) -> OpportunityScore:
    meta = read_opportunity_json(opportunity_id)
    artifacts = {}
    for filename in (
        "01-market-demand.md",
        "02-pain-mining.md",
        "03-icp.md",
        "04-competitors.md",
        "05-offer-doc.md",
        "06-pricing.md",
    ):
        try:
            artifacts[filename] = read_artifact(opportunity_id, filename)
        except FileNotFoundError:
            artifacts[filename] = ""

    result = compute_validation_result(meta=meta, artifacts=artifacts)
    now = datetime.now(timezone.utc)
    score = OpportunityScore(
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        overall=result.overall_score,
        demand=next((c.score for c in result.categories if c.category == "demand_strength"), 0.0),
        competition=next((c.score for c in result.categories if c.category == "competition_gap"), 0.0),
        differentiation=next((c.score for c in result.categories if c.category == "offer_clarity"), 0.0),
        feasibility=next((c.score for c in result.categories if c.category == "delivery_feasibility"), 0.0),
        notes=f"Recommendation: {result.recommendation}",
        source=source,
        created_at=now,
        updated_at=now,
    )
    update_opportunity_json(opportunity_id, {"scores": score.model_dump(mode="json")})
    return score


def render_validation_score_markdown(score: OpportunityScore) -> str:
    return (
        "# Validation Score\n\n"
        f"Overall: **{score.overall:.1f}/100**\n\n"
        "| Dimension | Score |\n"
        "|---|---:|\n"
        f"| Demand | {score.demand:.1f} |\n"
        f"| Competition gap | {score.competition:.1f} |\n"
        f"| Offer clarity | {score.differentiation:.1f} |\n"
        f"| Feasibility | {score.feasibility:.1f} |\n\n"
        f"{score.notes}\n"
    )


def score_phase() -> OpportunityPhase:
    return "validation_score"


__all__ = [
    "ValidationScoreInput",
    "compute_validation_score",
    "compute_weighted_overall",
    "recommendation_from_score",
    "render_validation_report",
    "render_validation_score_markdown",
    "run_validation_score_playbook",
    "score_phase",
]
