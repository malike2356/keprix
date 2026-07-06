"""CLI commands for generated tool management."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict

from keprix.agent.keprix.mutation import get_mutation_engine
from keprix.agent.keprix.store import get_generated_tool_store
from keprix.agent.keprix.installer import LiveInstaller


def cmd_tools_pending(_args) -> int:
    records = get_mutation_engine().list_pending()
    if not records:
        print("No pending generated tools.")
        return 0
    for record in records:
        print(f"{record.id}  {record.tool_name}  {record.status}")
    return 0


def cmd_tools_history(_args) -> int:
    records = get_generated_tool_store().list_all()
    for record in records:
        print(f"{record.id}  {record.tool_name}  {record.status}")
    return 0


def cmd_tools_show(args) -> int:
    record = get_generated_tool_store().get(args.record_id)
    if record is None:
        print(f"Not found: {args.record_id}", file=sys.stderr)
        return 1
    print(json.dumps(asdict(record), indent=2))
    return 0


def cmd_tools_approve(args) -> int:
    async def _run():
        return await get_mutation_engine().approve(args.record_id, approver_id="cli", channel="cli")

    result = asyncio.run(_run())
    if result is None:
        print(f"Could not approve: {args.record_id}", file=sys.stderr)
        return 1
    print(f"Approved and installed: {result.record.tool_name}")
    if result.retry_message:
        print(result.retry_message)
    return 0


def cmd_tools_reject(args) -> int:
    async def _run():
        return await get_mutation_engine().reject(
            args.record_id,
            approver_id="cli",
            channel="cli",
            reason=getattr(args, "reason", None),
        )

    record = asyncio.run(_run())
    if record is None:
        print(f"Could not reject: {args.record_id}", file=sys.stderr)
        return 1
    print(f"Rejected: {record.tool_name}")
    return 0


def cmd_tools_delete_generated(args) -> int:
    record = get_generated_tool_store().get(args.record_id)
    if record is None:
        print(f"Not found: {args.record_id}", file=sys.stderr)
        return 1
    removed = LiveInstaller().remove_from_filesystem(record)
    print("Removed from filesystem." if removed else "Nothing to remove on disk.")
    return 0
