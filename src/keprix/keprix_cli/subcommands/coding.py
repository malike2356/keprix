"""Coding agent CLI subcommand parsers."""

from __future__ import annotations

from typing import Callable


def build_coding_parser(
    subparsers,
    *,
    cmd_profiles: Callable,
    cmd_run: Callable,
    cmd_preflight_run: Callable,
    cmd_preflight_show: Callable,
    cmd_preflight_config: Callable,
) -> None:
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

    preflight_parser = coding_sub.add_parser("preflight", help="Run coding preflight gates")
    preflight_sub = preflight_parser.add_subparsers(dest="preflight_command", required=True)

    preflight_run = preflight_sub.add_parser("run", help="Run preflight for a session")
    preflight_run.add_argument("--session", required=True, dest="session_id")
    preflight_run.add_argument("--intent", default="")
    preflight_run.add_argument("--repo", default=None, dest="repo_path")
    preflight_run.add_argument("--planned-lines", type=int, default=None)
    preflight_run.add_argument("--provider-budget-pct", type=float, default=None)
    preflight_run.set_defaults(func=cmd_preflight_run)

    preflight_show = preflight_sub.add_parser("show", help="Show last preflight report")
    preflight_show.add_argument("--session", required=True, dest="session_id")
    preflight_show.set_defaults(func=cmd_preflight_show)

    preflight_config = preflight_sub.add_parser("config", help="Show preflight config")
    preflight_config.set_defaults(func=cmd_preflight_config)
