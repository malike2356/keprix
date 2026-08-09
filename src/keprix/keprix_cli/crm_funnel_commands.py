"""Handlers for ``keprix crm-funnel``."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def cmd_crm_funnel(args) -> int:
    command = getattr(args, "crm_funnel_command", None)
    ws = getattr(args, "workspace_id", None)
    if command == "tick":
        from keprix.crm.funnel_orchestrator import orchestrate

        result = orchestrate(
            str(ws),
            trigger=str(getattr(args, "trigger", "")),
            action=str(getattr(args, "action", "")),
            subject_id=str(getattr(args, "subject_id", "")),
            subject_type=str(getattr(args, "subject_type", "lead") or "lead"),
            idempotency_key=getattr(args, "idempotency_key", None),
            force=bool(getattr(args, "force", False)),
            approval_id=getattr(args, "approval_id", None),
            actor_type="cli",
            actor_id="cli",
        )
        sys.stdout.write(json.dumps(result, default=str, indent=2) + "\n")
        return 0 if result.get("ok") or result.get("blocked") or result.get("idempotent") else 1

    if command == "nba":
        from keprix.crm.next_best_action import execute_next_best_action, suggest_next_best_action

        if getattr(args, "execute", False):
            result = execute_next_best_action(
                str(ws),
                subject_id=str(getattr(args, "subject_id", "")),
                subject_type=str(getattr(args, "subject_type", "lead") or "lead"),
                force=bool(getattr(args, "force", False)),
                approval_id=getattr(args, "approval_id", None),
                actor_id="cli",
            )
        else:
            result = suggest_next_best_action(
                str(ws),
                subject_id=str(getattr(args, "subject_id", "")),
                subject_type=str(getattr(args, "subject_type", "lead") or "lead"),
            )
        sys.stdout.write(json.dumps(result, default=str, indent=2) + "\n")
        return 0

    if command == "journey":
        from keprix.crm.channel_journey import journey_status, run_channel_journey

        if getattr(args, "status_only", False) or not getattr(args, "file", None):
            result = journey_status(str(ws))
            sys.stdout.write(json.dumps(result, default=str, indent=2) + "\n")
            return 0
        path = Path(str(args.file))
        content = path.read_bytes()
        result = run_channel_journey(
            str(ws),
            payload=content,
            filename=path.name,
            channel=str(getattr(args, "channel", "cli") or "cli"),
            list_name=getattr(args, "list_name", None),
            force=bool(getattr(args, "force", False)),
            approval_id=getattr(args, "approval_id", None),
            actor_id="cli",
        )
        sys.stdout.write(json.dumps(result, default=str, indent=2) + "\n")
        return 0

    if command == "observability":
        from keprix.outreach.observability import collect_outreach_observability

        result = collect_outreach_observability(str(ws))
        sys.stdout.write(json.dumps(result, default=str, indent=2) + "\n")
        return 0 if result.get("complete") else 1

    sys.stderr.write(f"unknown crm-funnel command: {command}\n")
    return 2
