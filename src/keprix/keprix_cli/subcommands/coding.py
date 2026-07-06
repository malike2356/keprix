"""Coding agent CLI subcommand parsers."""

from __future__ import annotations

from typing import Callable


def build_coding_parser(subparsers, *, cmd_profiles: Callable, cmd_run: Callable) -> None:
    coding_parser = subparsers.add_parser(
        "coding",
        help="SWE-agent-style issue-to-patch runner",
        description="Run governed coding trajectories with scoped edits and audit logs.",
    )
    coding_sub = coding_parser.add_subparsers(dest="coding_command", required=True)

    profiles_parser = coding_sub.add_parser("profiles", help="List coding profiles")
    profiles_parser.set_defaults(func=cmd_profiles)

    run_parser = coding_sub.add_parser("run", help="Run issue-to-patch flow")
    run_parser.add_argument("issue", help="Issue text or GitHub issue URL")
    run_parser.add_argument("--repo", required=True, help="Repository path")
    run_parser.add_argument("--profile", default="default", help="Coding profile name")
    run_parser.add_argument("--test-command", default=None, help="Shell test command")
    run_parser.add_argument("--dry-run", action="store_true", help="Propose patch without applying")
    run_parser.add_argument("--approve", action="store_true", help="Mark human review approved")
    run_parser.set_defaults(func=cmd_run)
