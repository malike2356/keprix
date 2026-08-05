"""Coding agent CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.coding.configs import list_profiles
from keprix.coding.issue_runner import IssueRunRequest, run_issue
from keprix.coding.preflight_config import get_preflight_config
from keprix.coding.preflight_service import PreflightService
from keprix.coding.preflight_store import PreflightStore


def cmd_coding_profiles(_args) -> int:
    for name in list_profiles():
        print(name)
    return 0


def cmd_coding_run(args) -> int:
    result = run_issue(
        IssueRunRequest(
            issue=args.issue,
            repo_path=args.repo,
            test_command=args.test_command,
            profile=args.profile,
            human_approved=args.approve,
            dry_run=args.dry_run,
        )
    )
    print(json.dumps(result.__dict__, default=str, indent=2))
    return 0 if result.ok else 1


def cmd_coding_preflight_run(args) -> int:
    report = PreflightService().run(
        session_id=args.session_id,
        payload={
            "intent": args.intent,
            "repo_path": args.repo_path,
            "planned_lines": args.planned_lines,
            "provider_budget_pct": args.provider_budget_pct,
        },
    )
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.overall != "block" else 2


def cmd_coding_preflight_show(args) -> int:
    report = PreflightStore().get(args.session_id)
    if report is None:
        print(json.dumps({"error": "preflight report not found"}))
        return 1
    print(json.dumps(report.to_dict(), indent=2))
    return 0


def cmd_coding_preflight_config(_args) -> int:
    print(json.dumps(get_preflight_config().to_dict(), indent=2))
    return 0
