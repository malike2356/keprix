"""Research workspace CLI parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_research_parser(
    subparsers: _SubParsersAction,
    *,
    cmd_list: Callable,
    cmd_run: Callable,
    cmd_projects: Callable,
) -> None:
    research_parser = subparsers.add_parser(
        "research",
        help="Research workspace projects and YAML playbooks",
    )
    research_sub = research_parser.add_subparsers(dest="research_command", required=True)

    list_parser = research_sub.add_parser("list", help="List research playbooks")
    list_parser.set_defaults(func=cmd_list)

    projects_parser = research_sub.add_parser("projects", help="List research projects")
    projects_parser.add_argument("--workspace-id", default="default")
    projects_parser.set_defaults(func=cmd_projects)

    run_parser = research_sub.add_parser("run", help="Run a research playbook")
    run_parser.add_argument("project_id", help="Research project ID (rp-...)")
    run_parser.add_argument("playbook_id", help="Playbook ID (e.g. literature_review)")
    run_parser.add_argument("--dry-run", action="store_true", help="Fixture dry run without writes")
    run_parser.add_argument("--workspace-id", default="default")
    run_parser.set_defaults(func=cmd_run)
