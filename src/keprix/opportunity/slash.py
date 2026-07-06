"""Slash command parsing and execution for Opportunity Engine."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from keprix.opportunity.models import PHASE_ORDER, OpportunityRequest
from keprix.opportunity.orchestrator import run_opportunity_phase, run_opportunity_pipeline
from keprix.opportunity.registry import get_opportunity_registry
from keprix.opportunity.workspace import read_opportunity_json, update_opportunity_json

SlashAction = Literal[
    "help",
    "find_demand",
    "run_phase",
    "build_offer",
    "prepare_launch",
    "run_pipeline",
    "status",
]

PHASE_ALIASES: dict[str, str] = {
    "market-demand": "market_demand",
    "market_demand": "market_demand",
    "pain-mining": "pain_mining",
    "pain_mining": "pain_mining",
    "offer-builder": "offer_builder",
    "offer_builder": "offer_builder",
    "icp-builder": "icp_builder",
    "validation-score": "validation_score",
    "offer-doc": "offer_doc",
    "asset-factory": "asset_factory",
    "launch-orchestrator": "launch_orchestrator",
    "growth-loop": "growth_loop",
    "growth_loop": "growth_loop",
}


class OpportunitySlashIntent(BaseModel):
    action: SlashAction = "help"
    title: str = ""
    niche: str = ""
    goal: str = ""
    phase: str | None = None
    opportunity_id: str | None = None
    dry_run: bool = True
    pause_on_approval: bool = True
    needs_clarification: bool = False
    clarification: str = ""


class OpportunitySlashResult(BaseModel):
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


def _extract_for_clause(text: str) -> str:
    match = re.search(r"\bfor\s+(.+)$", text, re.I)
    if match:
        return match.group(1).strip().strip('"').strip("'")
    return ""


def _extract_title_from_demand(text: str) -> str:
    subject = _extract_for_clause(text)
    if subject:
        return subject[:80]
    cleaned = re.sub(r"^find\s+demand\s*", "", text, flags=re.I).strip()
    return cleaned[:80] or "Opportunity from slash command"


def parse_opportunity_slash(text: str) -> OpportunitySlashIntent:
    lowered = text.strip().lower()
    if not lowered or lowered in {"help", "?"}:
        return OpportunitySlashIntent(action="help")

    opp_id_match = re.search(r"\b(opp-[a-z0-9]{8})\b", text, re.I)
    opportunity_id = opp_id_match.group(1) if opp_id_match else None

    if "do not publish" in lowered or "dry run" in lowered or "dry-run" in lowered:
        dry_run = True
    elif "publish" in lowered:
        dry_run = False
    else:
        dry_run = True

    if lowered.startswith("find demand") or "find demand for" in lowered:
        niche = _extract_for_clause(text)
        if not niche:
            return OpportunitySlashIntent(
                action="find_demand",
                needs_clarification=True,
                clarification="Which niche or market should I research? Example: UK estate agencies",
            )
        return OpportunitySlashIntent(
            action="find_demand",
            title=_extract_title_from_demand(text),
            niche=niche,
            goal=f"Validate demand for {niche}",
            opportunity_id=opportunity_id,
            dry_run=dry_run,
        )

    phase_run = re.search(r"\brun\s+([\w-]+)\b", lowered)
    if phase_run:
        raw_phase = phase_run.group(1)
        phase = PHASE_ALIASES.get(raw_phase, raw_phase.replace("-", "_"))
        if phase not in PHASE_ORDER:
            return OpportunitySlashIntent(
                action="help",
                clarification=f"Unknown playbook phase `{raw_phase}`. Valid: {', '.join(PHASE_ORDER)}",
            )
        niche = _extract_for_clause(text)
        return OpportunitySlashIntent(
            action="run_phase",
            phase=phase,
            niche=niche,
            title=niche or "Slash opportunity",
            opportunity_id=opportunity_id,
            dry_run=dry_run,
        )

    if "build offer" in lowered:
        return OpportunitySlashIntent(
            action="build_offer",
            phase="offer_builder",
            opportunity_id=opportunity_id,
            dry_run=dry_run,
        )

    if "prepare launch" in lowered or "launch plan" in lowered:
        return OpportunitySlashIntent(
            action="prepare_launch",
            phase="launch_orchestrator",
            opportunity_id=opportunity_id,
            dry_run=True,
            pause_on_approval=True,
        )

    if lowered.startswith("run ") and "phase" not in lowered:
        return OpportunitySlashIntent(
            action="run_pipeline",
            opportunity_id=opportunity_id,
            dry_run=dry_run,
            pause_on_approval=True,
        )

    if lowered.startswith("status"):
        return OpportunitySlashIntent(action="status", opportunity_id=opportunity_id)

    return OpportunitySlashIntent(
        action="help",
        clarification=(
            "Usage examples:\n"
            "- /opportunity find demand for AI automation in UK estate agencies\n"
            "- /opportunity run market-demand for property maintenance SaaS\n"
            "- /opportunity build offer from this demand report\n"
            "- /opportunity prepare launch plan but do not publish"
        ),
    )


def _resolve_or_create_opportunity(
    *,
    intent: OpportunitySlashIntent,
    workspace_id: str,
    user_id: str,
) -> str:
    if intent.opportunity_id:
        return intent.opportunity_id

    registry = get_opportunity_registry()
    records = registry.list_for_user(user_id)
    if records:
        return records[0].opportunity_id

    title = intent.title or intent.niche or "Slash opportunity"
    workspace = registry.create(
        user_id=user_id,
        request=OpportunityRequest(
            workspace_id=workspace_id,
            title=title,
            niche=intent.niche or None,
            goal=intent.goal or title,
            source="slash",
        ),
    )
    return workspace.opportunity_id


async def execute_opportunity_slash(
    intent: OpportunitySlashIntent,
    *,
    workspace_id: str,
    user_id: str,
) -> OpportunitySlashResult:
    if intent.action == "help":
        message = intent.clarification or (
            "Opportunity Engine slash commands default to dry run for launch actions.\n"
            "Use find demand, run <playbook phase>, build offer, or prepare launch plan."
        )
        return OpportunitySlashResult(summary=message)

    if intent.needs_clarification:
        return OpportunitySlashResult(summary=intent.clarification)

    opportunity_id = _resolve_or_create_opportunity(
        intent=intent,
        workspace_id=workspace_id,
        user_id=user_id,
    )

    if intent.action == "status":
        meta = read_opportunity_json(opportunity_id)
        return OpportunitySlashResult(
            summary=(
                f"Opportunity `{opportunity_id}` status: {meta.get('status', 'draft')}\n"
                f"Current playbook phase: {meta.get('current_phase') or 'none'}\n"
                f"Pending approvals: {len(meta.get('pending_approvals') or [])}"
            ),
            payload={"opportunity_id": opportunity_id, "meta": meta},
        )

    if intent.action == "run_pipeline":
        result = await run_opportunity_pipeline(
            opportunity_id,
            {"pause_on_approval": intent.pause_on_approval},
        )
        return OpportunitySlashResult(
            summary=f"Pipeline run for `{opportunity_id}` completed ({len(result.get('phases', []))} phases).",
            payload=result,
        )

    phase = intent.phase
    if intent.action == "find_demand":
        phase = "market_demand"
    elif intent.action == "build_offer":
        phase = "offer_builder"
    elif intent.action == "prepare_launch":
        phase = "launch_orchestrator"
        update_opportunity_json(opportunity_id, {"launch_dry_run": intent.dry_run})

    if not phase:
        return OpportunitySlashResult(summary="No playbook phase resolved.")

    result = await run_opportunity_phase(opportunity_id, phase)  # type: ignore[arg-type]
    meta = read_opportunity_json(opportunity_id)
    pending = meta.get("pending_approvals") or []
    approval_lines = [
        f"- {row.get('action')}: {row.get('reason', '')[:120]}"
        for row in pending[:5]
    ]
    summary = (
        f"Playbook phase `{phase}` finished for `{opportunity_id}`.\n"
        f"Artifacts: {', '.join(result.get('artifacts_written') or []) or 'none'}\n"
        f"Next: review approvals before any publish or spend actions."
    )
    if approval_lines:
        summary += "\nApproval requirements:\n" + "\n".join(approval_lines)
    if intent.dry_run and phase == "launch_orchestrator":
        summary += "\nLaunch plan prepared in dry run mode (not published)."

    return OpportunitySlashResult(
        summary=summary,
        payload={"opportunity_id": opportunity_id, "phase_result": result},
    )
