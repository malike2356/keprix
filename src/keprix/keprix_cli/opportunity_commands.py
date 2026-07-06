"""Opportunity Engine CLI commands."""

from __future__ import annotations

import asyncio
import json

from keprix.opportunity.approvals import resolve_approval
from keprix.opportunity.models import OpportunityRequest, PHASE_ORDER
from keprix.opportunity.orchestrator import run_opportunity_phase, run_opportunity_pipeline
from keprix.opportunity.registry import get_opportunity_registry
from keprix.opportunity.workspace import read_artifact, read_opportunity_json


def cmd_opportunity_new(args) -> int:
    registry = get_opportunity_registry()
    request = OpportunityRequest(
        workspace_id=args.workspace_id,
        title=args.title,
        niche=args.niche,
        market=args.market,
        goal=args.goal,
        source="cli",
    )
    workspace = registry.create(user_id="cli", request=request)
    print(json.dumps(workspace.model_dump(mode="json"), indent=2, default=str))
    return 0


def cmd_opportunity_run(args) -> int:
    options: dict[str, object] = {}
    if args.pause_on_approval:
        options["pause_on_approval"] = True
    result = asyncio.run(run_opportunity_pipeline(args.opportunity_id, options or None))
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_opportunity_phase(args) -> int:
    phase = args.phase.strip().lower()
    if phase not in PHASE_ORDER:
        print(json.dumps({"error": f"Unknown phase: {phase}", "valid": PHASE_ORDER}, indent=2))
        return 1
    result = asyncio.run(run_opportunity_phase(args.opportunity_id, phase))
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_opportunity_status(args) -> int:
    registry = get_opportunity_registry()
    record = registry.get(args.opportunity_id)
    if record is None:
        print(json.dumps({"error": "Opportunity not found"}, indent=2))
        return 1
    meta = read_opportunity_json(args.opportunity_id)
    print(json.dumps({"record": record.to_dict(), "meta": meta}, indent=2, default=str))
    return 0


def cmd_opportunity_artifact(args) -> int:
    try:
        content = read_artifact(args.opportunity_id, args.filename)
    except FileNotFoundError:
        print(json.dumps({"error": f"Artifact not found: {args.filename}"}, indent=2))
        return 1
    if getattr(args, "json", False):
        print(json.dumps({"filename": args.filename, "content": content}, indent=2))
    else:
        print(content)
    return 0


def cmd_opportunity_approve(args) -> int:
    registry = get_opportunity_registry()
    record = registry.get(args.opportunity_id)
    if record is None:
        print(json.dumps({"error": "Opportunity not found"}, indent=2))
        return 1
    resolved = resolve_approval(
        workspace_id=record.workspace_id,
        opportunity_id=args.opportunity_id,
        approval_id=args.approval_id,
        approved=not args.reject,
        approved_by="cli",
    )
    if resolved is None:
        print(json.dumps({"error": "Approval request not found"}, indent=2))
        return 1
    print(json.dumps(resolved.model_dump(mode="json"), indent=2, default=str))
    return 0
