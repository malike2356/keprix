"""Handlers for ``keprix outreach-scheduler``."""

from __future__ import annotations

import json
import sys


def cmd_outreach_scheduler(args) -> int:
    command = getattr(args, "outreach_scheduler_command", None)
    if command == "tick":
        from keprix.outreach.scheduler import run_scheduler_tick

        result = run_scheduler_tick(
            getattr(args, "workspace_id", None),
            limit=int(getattr(args, "limit", 50) or 50),
            worker_id=getattr(args, "worker_id", None),
            lease_seconds=int(getattr(args, "lease_seconds", 60) or 60),
            dry_run=bool(getattr(args, "dry_run", False)),
        )
        sys.stdout.write(json.dumps(result, default=str, indent=2) + "\n")
        return 0
    if command == "health":
        from keprix.outreach.store import get_outreach_store

        health = get_outreach_store().get_scheduler_health(getattr(args, "workspace_id", None))
        sys.stdout.write(json.dumps(health, default=str, indent=2) + "\n")
        return 0
    sys.stderr.write(f"unknown outreach-scheduler command: {command}\n")
    return 2
