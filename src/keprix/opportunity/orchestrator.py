"""Opportunity phase orchestrator and pipeline runner."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from keprix.opportunity.citations import add_citation, format_citations_block, list_citations
from keprix.opportunity.models import PHASE_ARTIFACT_MAP, PHASE_ORDER, OpportunityPhase
from keprix.opportunity.playbooks.market_demand import MarketDemandInput, run_market_demand_playbook
from keprix.opportunity.playbooks.pain_mining import build_pain_mining_input_from_meta, run_pain_mining_playbook
from keprix.opportunity.playbooks.offer_builder import (
    build_offer_builder_input_from_meta,
    run_offer_builder_playbook,
)
from keprix.opportunity.playbooks.icp_builder import (
    _extract_offer_fields,
    build_icp_builder_input_from_meta,
    run_icp_builder_playbook,
)
from keprix.opportunity.playbooks.competitor_intelligence import (
    build_competitor_intelligence_input_from_meta,
    run_competitor_intelligence_playbook,
)
from keprix.opportunity.playbooks.offer_doc_generator import run_offer_doc_generator_playbook
from keprix.opportunity.playbooks.asset_factory import AssetFactoryInput, run_asset_factory_playbook
from keprix.opportunity.playbooks.growth_loop import run_growth_loop_playbook
from keprix.opportunity.playbooks.launch_orchestrator import run_launch_orchestrator_playbook
from keprix.opportunity.playbooks.validation_score import (
    ValidationBlockedError,
    ValidationScoreInput,
    run_validation_score_playbook,
)
from keprix.opportunity.registry import get_opportunity_registry
from keprix.opportunity.safety import run_content_safety_checks
from keprix.opportunity.workspace import (
    read_artifact,
    read_opportunity_json,
    update_opportunity_json,
    write_artifact,
    write_opportunity_asset,
)
from keprix.research.search import web_search


def _emit_event(opportunity_id: str, event_type: str, payload: dict[str, Any]) -> None:
    registry = get_opportunity_registry()
    registry.append_event(opportunity_id, event_type, payload)
    try:
        from keprix.observability.metrics import get_metrics_store

        store = get_metrics_store()
        loop = asyncio.get_running_loop()
        loop.create_task(
            store.record(
                metric_type="opportunity",
                metric_name=event_type,
                metric_value=1,
                tags={"opportunity_id": opportunity_id, **payload},
            )
        )
    except Exception:
        pass


def _context(opportunity_id: str) -> dict[str, Any]:
    meta = read_opportunity_json(opportunity_id)
    title = meta.get("title", "Opportunity")
    niche = meta.get("niche") or meta.get("market") or title
    goal = meta.get("goal") or title
    return {
        "workspace_id": meta["workspace_id"],
        "opportunity_id": opportunity_id,
        "title": title,
        "niche": niche,
        "goal": goal,
        "meta": meta,
    }


async def _research_for_phase(
    *,
    workspace_id: str,
    opportunity_id: str,
    phase: OpportunityPhase,
    query: str,
    artifact_filename: str | None = None,
) -> list[dict[str, Any]]:
    results = await web_search(query, limit=5)
    for item in results:
        url = str(item.get("url", ""))
        if not url:
            continue
        add_citation(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            url=url,
            title=str(item.get("title", "")),
            snippet=str(item.get("snippet", "")),
            phase=phase,
            artifact_filename=artifact_filename,
        )
    return results


async def _run_market_demand(ctx: dict[str, Any]) -> str:
    meta = ctx["meta"]
    request = MarketDemandInput(
        niche=ctx["niche"],
        geography=meta.get("geography"),
        buyer_type=meta.get("buyer_type"),
        budget_range=meta.get("budget_range"),
        exclusions=meta.get("exclusions") or [],
        research_depth=meta.get("research_depth", "standard"),
    )
    return await run_market_demand_playbook(
        workspace_id=ctx["workspace_id"],
        opportunity_id=ctx["opportunity_id"],
        request=request,
        title=ctx["title"],
        goal=ctx["goal"],
        user_id=meta.get("user_id", "local"),
    )


async def _run_pain_mining(ctx: dict[str, Any]) -> str:
    request = build_pain_mining_input_from_meta(ctx["meta"])
    return await run_pain_mining_playbook(
        workspace_id=ctx["workspace_id"],
        opportunity_id=ctx["opportunity_id"],
        request=request,
    )


async def _run_offer_builder(ctx: dict[str, Any]) -> tuple[str, str]:
    request = build_offer_builder_input_from_meta(ctx["meta"])
    return await run_offer_builder_playbook(
        workspace_id=ctx["workspace_id"],
        opportunity_id=ctx["opportunity_id"],
        request=request,
    )


async def _run_icp_builder(ctx: dict[str, Any]) -> str:
    offer_md = ""
    try:
        offer_md = read_artifact(ctx["opportunity_id"], "05-offer-doc.md")
    except FileNotFoundError:
        pass
    offer_fields = _extract_offer_fields(offer_md, ctx["meta"])
    request = build_icp_builder_input_from_meta(ctx["meta"], offer_fields=offer_fields)
    return await run_icp_builder_playbook(
        workspace_id=ctx["workspace_id"],
        opportunity_id=ctx["opportunity_id"],
        request=request,
    )


async def _run_competitor_intelligence(ctx: dict[str, Any]) -> str:
    icp_md = ""
    offer_md = ""
    try:
        icp_md = read_artifact(ctx["opportunity_id"], "03-icp.md")
    except FileNotFoundError:
        pass
    try:
        offer_md = read_artifact(ctx["opportunity_id"], "05-offer-doc.md")
    except FileNotFoundError:
        pass
    request = build_competitor_intelligence_input_from_meta(
        ctx["meta"],
        icp_md=icp_md,
        offer_md=offer_md,
    )
    return await run_competitor_intelligence_playbook(
        workspace_id=ctx["workspace_id"],
        opportunity_id=ctx["opportunity_id"],
        request=request,
    )


async def _run_validation_score(ctx: dict[str, Any]) -> str:
    override = bool(ctx.get("meta", {}).get("validation_override"))
    request = ValidationScoreInput(
        user_override=override,
        override_by=str(ctx["meta"].get("override_by", "system")),
        override_reason=str(ctx["meta"].get("override_reason", "")),
    )
    return await run_validation_score_playbook(
        workspace_id=ctx["workspace_id"],
        opportunity_id=ctx["opportunity_id"],
        request=request,
    )


async def _run_offer_doc(ctx: dict[str, Any]) -> tuple[str, str]:
    user_id = str(ctx["meta"].get("user_id") or "local")
    return await run_offer_doc_generator_playbook(
        workspace_id=ctx["workspace_id"],
        opportunity_id=ctx["opportunity_id"],
        user_id=user_id,
    )


async def _run_asset_factory(ctx: dict[str, Any]) -> dict[str, str]:
    request = AssetFactoryInput(
        brand_preferences=dict(ctx["meta"].get("brand_preferences") or {}),
        asset_selection=list(ctx["meta"].get("asset_selection") or []),
    )
    return await run_asset_factory_playbook(
        workspace_id=ctx["workspace_id"],
        opportunity_id=ctx["opportunity_id"],
        request=request,
    )


async def _run_launch_orchestrator(ctx: dict[str, Any]) -> str:
    dry_run = bool(ctx.get("meta", {}).get("launch_dry_run", True))
    requested_by = str(ctx.get("meta", {}).get("user_id") or "system")
    return await run_launch_orchestrator_playbook(
        workspace_id=ctx["workspace_id"],
        opportunity_id=ctx["opportunity_id"],
        dry_run=dry_run,
        requested_by=requested_by,
    )


async def _run_growth_loop(ctx: dict[str, Any]) -> str:
    requested_by = str(ctx.get("meta", {}).get("user_id") or "system")
    result = await run_growth_loop_playbook(
        workspace_id=ctx["workspace_id"],
        opportunity_id=ctx["opportunity_id"],
        requested_by=requested_by,
    )
    return result.report_md


_PHASE_RUNNERS = {
    "market_demand": _run_market_demand,
    "pain_mining": _run_pain_mining,
    "offer_builder": _run_offer_builder,
    "icp_builder": _run_icp_builder,
    "competitor_intelligence": _run_competitor_intelligence,
    "validation_score": _run_validation_score,
    "offer_doc": _run_offer_doc,
    "asset_factory": _run_asset_factory,
    "launch_orchestrator": _run_launch_orchestrator,
    "growth_loop": _run_growth_loop,
}


async def run_opportunity_phase(
    opportunity_id: str,
    phase: OpportunityPhase,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if phase not in PHASE_ORDER:
        raise ValueError(f"Unknown phase: {phase}")

    ctx = _context(opportunity_id)
    if options:
        if options.get("validation_override"):
            update_opportunity_json(
                opportunity_id,
                {
                    "validation_override": True,
                    "override_by": options.get("override_by", "user"),
                    "override_reason": options.get("override_reason", "pipeline override"),
                },
            )
            ctx = _context(opportunity_id)
    _emit_event(opportunity_id, "opportunity.phase.started", {"phase": phase})

    status_map = {
        "market_demand": "researching",
        "pain_mining": "researching",
        "competitor_intelligence": "researching",
        "validation_score": "validating",
        "asset_factory": "assets_ready",
        "launch_orchestrator": "approval_required",
    }
    if phase in status_map:
        update_opportunity_json(opportunity_id, {"status": status_map[phase], "current_phase": phase})

    runner = _PHASE_RUNNERS[phase]
    try:
        result: Any = await runner(ctx)
    except ValidationBlockedError as exc:
        _emit_event(
            opportunity_id,
            "opportunity.phase.blocked",
            {
                "phase": phase,
                "overall_score": exc.result.overall_score,
                "recommendation": exc.result.recommendation,
            },
        )
        return {
            "phase": phase,
            "blocked": True,
            "overall_score": exc.result.overall_score,
            "recommendation": exc.result.recommendation,
            "artifacts_written": [],
        }

    artifacts_written: list[str] = []
    if phase in ("offer_builder", "offer_doc"):
        _offer_doc, _pricing = result
        artifacts_written = ["05-offer-doc.md", "06-pricing.md"]
        if phase == "offer_doc":
            artifacts_written.append("agent-memory-brief.md")
    elif phase == "asset_factory":
        for filename, content in result.items():
            if filename.startswith("assets/"):
                write_opportunity_asset(
                    opportunity_id,
                    filename.removeprefix("assets/"),
                    content,
                )
            else:
                write_artifact(opportunity_id, filename, content)
            artifacts_written.append(filename)
    else:
        for filename in PHASE_ARTIFACT_MAP[phase]:
            write_artifact(opportunity_id, filename, str(result))
            artifacts_written.append(filename)

    meta = read_opportunity_json(opportunity_id)
    completed = list(meta.get("completed_phases", []))
    if phase not in completed:
        completed.append(phase)
    update_opportunity_json(
        opportunity_id,
        {
            "completed_phases": completed,
            "current_phase": phase,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    registry = get_opportunity_registry()
    if registry.get(opportunity_id):
        registry.update_status(opportunity_id, read_opportunity_json(opportunity_id).get("status", "draft"))

    payload = {
        "phase": phase,
        "artifacts_written": artifacts_written,
        "options": options or {},
    }
    _emit_event(opportunity_id, "opportunity.phase.completed", payload)
    return payload


async def run_opportunity_pipeline(
    opportunity_id: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    phases = list(PHASE_ORDER)
    if options and options.get("stop_at"):
        stop_at = options["stop_at"]
        if stop_at in phases:
            phases = phases[: phases.index(stop_at) + 1]

    results: list[dict[str, Any]] = []
    _emit_event(opportunity_id, "opportunity.pipeline.started", {"phases": phases})
    for phase in phases:
        result = await run_opportunity_phase(opportunity_id, phase, options)
        results.append(result)
        if result.get("blocked"):
            break
        if options and options.get("pause_on_approval"):
            meta = read_opportunity_json(opportunity_id)
            if meta.get("status") == "approval_required":
                break

    meta = read_opportunity_json(opportunity_id)
    if meta.get("status") not in {"approval_required", "paused", "archived"}:
        update_opportunity_json(opportunity_id, {"status": "launch_ready"})
        registry = get_opportunity_registry()
        if registry.get(opportunity_id):
            registry.update_status(opportunity_id, "launch_ready")

    _emit_event(
        opportunity_id,
        "opportunity.pipeline.completed",
        {"phases_run": [row["phase"] for row in results]},
    )
    return {"opportunity_id": opportunity_id, "phases": results}
