"""Coding agent CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.coding.configs import list_profiles
from keprix.coding.issue_runner import IssueRunRequest, run_issue


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
