"""Pydantic models for the Opportunity Engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

OpportunityStatus = Literal[
    "draft",
    "researching",
    "validating",
    "assets_ready",
    "approval_required",
    "launch_ready",
    "launched",
    "paused",
    "archived",
]

OpportunityPhase = Literal[
    "market_demand",
    "pain_mining",
    "offer_builder",
    "icp_builder",
    "competitor_intelligence",
    "validation_score",
    "offer_doc",
    "asset_factory",
    "launch_orchestrator",
    "growth_loop",
]

PHASE_ORDER: list[OpportunityPhase] = [
    "market_demand",
    "pain_mining",
    "offer_builder",
    "icp_builder",
    "competitor_intelligence",
    "validation_score",
    "offer_doc",
    "asset_factory",
    "launch_orchestrator",
    "growth_loop",
]

PHASE_ARTIFACT_MAP: dict[OpportunityPhase, list[str]] = {
    "market_demand": ["01-market-demand.md"],
    "pain_mining": ["02-pain-mining.md"],
    "offer_builder": ["05-offer-doc.md", "06-pricing.md"],
    "icp_builder": ["03-icp.md"],
    "competitor_intelligence": ["04-competitors.md"],
    "validation_score": ["12-validation-score.md"],
    "offer_doc": ["05-offer-doc.md", "agent-memory-brief.md"],
    "asset_factory": ["07-funnel.md", "08-content-assets.md", "09-ads.md", "10-sales-deck.md"],
    "launch_orchestrator": ["11-launch-plan.md"],
    "growth_loop": ["14-growth-loop.md"],
}

ARTIFACT_FILENAMES: list[str] = [
    "01-market-demand.md",
    "02-pain-mining.md",
    "03-icp.md",
    "04-competitors.md",
    "05-offer-doc.md",
    "06-pricing.md",
    "07-funnel.md",
    "08-content-assets.md",
    "09-ads.md",
    "10-sales-deck.md",
    "11-launch-plan.md",
    "12-validation-score.md",
    "13-approval-log.md",
    "14-growth-loop.md",
    "agent-memory-brief.md",
    "opportunity.json",
]

ASSET_FOLDER_FILENAMES: list[str] = [
    "landing-page.md",
    "lead-magnet.md",
    "email-nurture-sequence.md",
    "linkedin-posts.md",
    "short-video-scripts.md",
    "ad-copy.md",
    "sales-deck.md",
    "logo-brief.md",
    "brand-brief.md",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OpportunityBase(BaseModel):
    workspace_id: str
    opportunity_id: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    source: str = "api"


class OpportunityWorkspace(OpportunityBase):
    slug: str
    title: str
    niche: str | None = None
    market: str | None = None
    goal: str | None = None
    status: OpportunityStatus = "draft"
    current_phase: OpportunityPhase | None = None
    completed_phases: list[OpportunityPhase] = Field(default_factory=list)
    path: str = ""


class OpportunityRequest(BaseModel):
    workspace_id: str = "default"
    title: str = Field(..., min_length=1)
    niche: str | None = None
    market: str | None = None
    goal: str | None = None
    geography: str | None = None
    buyer_type: str | None = None
    budget_range: str | None = None
    exclusions: list[str] = Field(default_factory=list)
    research_depth: str = "standard"
    source: str = "api"


class OpportunityArtifact(OpportunityBase):
    filename: str
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class OpportunityCitation(OpportunityBase):
    citation_id: str
    url: str
    title: str = ""
    snippet: str = ""
    phase: OpportunityPhase | None = None
    artifact_filename: str | None = None


class OpportunityScore(OpportunityBase):
    overall: float = 0.0
    demand: float = 0.0
    competition: float = 0.0
    differentiation: float = 0.0
    feasibility: float = 0.0
    notes: str = ""


class OpportunityApproval(OpportunityBase):
    approval_id: str
    action: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    requested_by: str = "system"
    approved_by: str | None = None
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class OpportunityExecutionPlan(OpportunityBase):
    plan_id: str
    phases: list[OpportunityPhase] = Field(default_factory=list)
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)


class OpportunityIntegrationRef(OpportunityBase):
    integration_id: str
    provider: str
    capability: str
    configured: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
