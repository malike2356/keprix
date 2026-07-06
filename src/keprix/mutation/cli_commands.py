"""CLI commands for mutation pipeline store (Prompt 151)."""

from __future__ import annotations

import asyncio
import json
import sys

from keprix.mutation.config import get_mutation_settings
from keprix.mutation.store import get_mutation_store
from keprix.mutation.tool_synthesizer import synthesize_tool
from keprix.improvement.tool_gap_detector import ToolGapProposal


def _workspace_id() -> str:
    return "default"


def cmd_mutation_list(args) -> int:
    store = get_mutation_store()
    items, total = store.list_mutations(
        _workspace_id(),
        tier=getattr(args, "tier", None),
        status=getattr(args, "status", None),
        page=1,
        per_page=200,
    )
    if not items:
        print("No mutations found.")
        return 0
    print(f"{'ID':<38}  {'NAME':<24}  {'TIER':<8}  {'STATUS':<10}")
    for item in items:
        print(f"{item.id:<38}  {item.name:<24}  {item.tier:<8}  {item.status:<10}")
    print(f"\nTotal: {total}")
    return 0


def cmd_mutation_approve(args) -> int:
    record = get_mutation_store().approve_mutation(args.mutation_id, approved_by="cli")
    if record is None:
        print(f"Not found: {args.mutation_id}", file=sys.stderr)
        return 1
    print(f"Approved: {record.name} ({record.id})")
    return 0


def cmd_mutation_reject(args) -> int:
    reason = getattr(args, "reason", "") or ""
    record = get_mutation_store().reject_mutation(args.mutation_id, rejected_by="cli", reason=reason)
    if record is None:
        print(f"Not found: {args.mutation_id}", file=sys.stderr)
        return 1
    print(f"Rejected: {record.name} ({record.id})")
    return 0


def cmd_mutation_rollback(args) -> int:
    record = get_mutation_store().rollback_mutation(args.mutation_id, rolled_back_by="cli")
    if record is None:
        print(f"Not found: {args.mutation_id}", file=sys.stderr)
        return 1
    print(f"Rolled back: {record.name} (rollback id {record.id})")
    return 0


def cmd_mutation_synthesize(args) -> int:
    settings = get_mutation_settings()
    store = get_mutation_store()
    proposal = ToolGapProposal(
        proposal_id="cli",
        tool_name=args.name,
        description=args.description,
        confidence=settings.auto_approve_threshold,
    )

    async def _run():
        return await synthesize_tool(proposal, _workspace_id())

    result = asyncio.run(_run())
    if not result.success or not result.source_code:
        print(result.error or "synthesis failed", file=sys.stderr)
        return 1
    record = store.save_generated_tool(
        workspace_id=_workspace_id(),
        tool_name=result.tool_name,
        description=args.description,
        source_code=result.source_code,
        trigger="cli",
        confidence=proposal.confidence,
        auto_approve_threshold=settings.auto_approve_threshold,
    )
    if record.status == "approved":
        generated_dir = store.generated_tools_dir()
        store.write_tool_to_disk(record, generated_dir)
        store.reload_registry(generated_dir)
    print(json.dumps({"id": record.id, "name": record.name, "status": record.status}))
    return 0


def cmd_mutation_stats(_args) -> int:
    stats = get_mutation_store().mutation_stats(_workspace_id())
    print(json.dumps(stats, indent=2))
    return 0


def cmd_mutation_code_request(args) -> int:
    from pathlib import Path

    from keprix.mutation.self_coding_harness import SelfCodingRequest, run_scoped_mutation

    settings = get_mutation_settings()
    if not settings.self_coding:
        print("Self-coding mutation is disabled.", file=sys.stderr)
        return 1

    request = SelfCodingRequest(
        task=args.task,
        target_dir=args.target_dir,
        workspace_id=_workspace_id(),
        requested_by="operator",
    )

    async def _run():
        return await run_scoped_mutation(
            request,
            get_mutation_store(),
            Path(settings.repo_root).resolve(),
        )

    result = asyncio.run(_run())
    if result.mutation_id is None:
        print(result.error or "mutation failed", file=sys.stderr)
        return 1
    print(json.dumps({"mutation_id": result.mutation_id, "branch_name": result.branch_name}))
    return 0


def cmd_mutation_code_list(args) -> int:
    items, total = get_mutation_store().list_mutations(
        _workspace_id(),
        tier="code",
        status=getattr(args, "status", None),
        page=1,
        per_page=200,
    )
    for item in items:
        print(f"{item.id}  {item.status}  {item.metadata.get('branch_name', '')}")
    print(f"Total: {total}")
    return 0


def cmd_mutation_code_diff(args) -> int:
    record = get_mutation_store().get_generated_tool(args.mutation_id)
    if record is None or record.tier != "code":
        print("Not found", file=sys.stderr)
        return 1
    print(record.source_code or "")
    return 0


def cmd_mutation_code_approve(args) -> int:
    record = get_mutation_store().approve_mutation(args.mutation_id, approved_by="cli")
    if record is None:
        print("Approve failed", file=sys.stderr)
        return 1
    print(f"Approved: {record.id}")
    return 0


def cmd_mutation_code_reject(args) -> int:
    record = get_mutation_store().reject_mutation(
        args.mutation_id,
        rejected_by="cli",
        reason=getattr(args, "reason", "") or "",
    )
    if record is None:
        print("Reject failed", file=sys.stderr)
        return 1
    print(f"Rejected: {record.id}")
    return 0


def cmd_mutation_code_rollback(args) -> int:
    record = get_mutation_store().rollback_mutation(args.mutation_id, rolled_back_by="cli")
    if record is None:
        print("Rollback failed", file=sys.stderr)
        return 1
    print(f"Rolled back: {record.id}")
    return 0
