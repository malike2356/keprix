"""Auto-improvement loop routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.improvement.eval_backfill import list_eval_cases, proposal_to_eval_case, save_eval_case
from keprix.improvement.feedback_collector import FeedbackCollector
from keprix.improvement.monitoring import collect_metrics, metrics_to_dict
from keprix.improvement.prompt_improver import propose_prompt_improvements
from keprix.improvement.run_analyzer import RunAnalyzer, RunRecord
from keprix.improvement.tool_gap_detector import detect_tool_gaps
from keprix.mutation.config import get_mutation_settings
from keprix.mutation.hook import schedule_on_run_complete
from keprix.mutation.prompt_confidence import estimate_confidence
from keprix.mutation.prompt_store import get_prompt_store
from keprix.public_api.auth import require_developer_session

router = APIRouter(prefix="/api/improvement", tags=["improvement"])


class RunBody(BaseModel):
    run_id: str
    agent_id: str
    ok: bool
    steps: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    eval_score: float | None = None
    cost_usd: float = 0.0
    user_corrections: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeedbackBody(BaseModel):
    run_id: str
    agent_id: str
    kind: str
    content: str
    satisfaction: int | None = None


class ApproveBody(BaseModel):
    proposal_id: str
    create_eval_case: bool = True


class ProposalIdBody(BaseModel):
    proposal_id: str


@router.post("/runs")
async def record_run(body: RunBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    analyzer = RunAnalyzer()
    record = RunRecord(
        run_id=body.run_id,
        agent_id=body.agent_id,
        ok=body.ok,
        steps=body.steps,
        tool_calls=body.tool_calls,
        eval_score=body.eval_score,
        cost_usd=body.cost_usd,
        user_corrections=body.user_corrections,
        metadata=body.metadata,
    )
    analyzer.save_run(record)
    proposals = analyzer.analyze(record)
    prompt_improvements = propose_prompt_improvements(record, proposals)
    tool_gaps = detect_tool_gaps(record, proposals)
    settings = get_mutation_settings()
    workspace_id = body.metadata.get("workspace_id", "default")
    if settings.enabled and settings.prompt_evolution:
        prompt_store = get_prompt_store()
        proposal_by_id = {proposal.proposal_id: proposal for proposal in proposals}
        for improvement in prompt_improvements:
            linked = proposal_by_id.get(improvement.proposal_id)
            category = linked.category if linked is not None else "low_eval"
            prompt_key = record.metadata.get("persona_id", improvement.current_prompt_hint or "default")
            prompt_store.stage_improvement(
                workspace_id=workspace_id,
                prompt_key=str(prompt_key).lower(),
                suggested_content=improvement.suggested_prompt,
                rationale=improvement.rationale,
                confidence=estimate_confidence(category),
                auto_approve_threshold=settings.auto_approve_threshold,
            )
    if settings.enabled and settings.tool_synthesis:
        schedule_on_run_complete(record, proposals, workspace_id=workspace_id)
    if settings.enabled and settings.prompt_evolution:
        from keprix.mutation.quality import classify_run_outcome, get_quality_scorer

        get_quality_scorer().record_prompt_use(
            workspace_id=workspace_id,
            prompt_key=str(record.metadata.get("persona_id", "default")),
            run_id=record.run_id,
            outcome=classify_run_outcome(record, proposals),
        )
    return {
        "run_id": record.run_id,
        "proposal_count": len(proposals),
        "proposals": [proposal.to_dict() for proposal in proposals],
        "prompt_improvements": [item.__dict__ for item in prompt_improvements],
        "tool_gaps": [item.__dict__ for item in tool_gaps],
    }


@router.post("/feedback")
async def record_feedback(body: FeedbackBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    record = FeedbackCollector().record(
        run_id=body.run_id,
        agent_id=body.agent_id,
        kind=body.kind,
        content=body.content,
        satisfaction=body.satisfaction,
    )
    return record.to_dict()


@router.get("/proposals")
async def list_proposals(status: str | None = None, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    proposals = RunAnalyzer().list_proposals(status=status)
    return {"proposals": [proposal.to_dict() for proposal in proposals]}


@router.post("/proposals/approve")
async def approve_proposal(body: ApproveBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    analyzer = RunAnalyzer()
    proposal = analyzer.approve_proposal(body.proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    eval_case = None
    if body.create_eval_case:
        record = analyzer.load_run(proposal.run_id)
        if record is not None:
            eval_case = proposal_to_eval_case(record, proposal)
            save_eval_case(eval_case)
    return {
        "proposal": proposal.to_dict(),
        "eval_case": eval_case.to_dict() if eval_case else None,
    }


@router.post("/proposals/reject")
async def reject_proposal(body: ProposalIdBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    proposal = RunAnalyzer().reject_proposal(body.proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    return {"proposal": proposal.to_dict()}


@router.post("/proposals/apply")
async def apply_proposal(body: ProposalIdBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    proposal = RunAnalyzer().apply_proposal(body.proposal_id)
    if proposal is None:
        raise HTTPException(status_code=409, detail="proposal not applicable")
    return {"proposal": proposal.to_dict()}


@router.post("/proposals/defer")
async def defer_proposal(body: ProposalIdBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    proposal = RunAnalyzer().defer_proposal(body.proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    return {"proposal": proposal.to_dict()}


@router.get("/eval-cases")
async def get_eval_cases(proposal_id: str | None = None, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    cases = list_eval_cases(proposal_id=proposal_id)
    return {"eval_cases": [case.to_dict() for case in cases]}


@router.get("/metrics")
async def improvement_metrics(agent_id: str | None = None, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    return metrics_to_dict(collect_metrics(agent_id=agent_id))
