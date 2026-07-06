"""Builder CLI parser (Prompt 29)."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_builder_parser(
    subparsers: _SubParsersAction,
    *,
    cmd_list: Callable,
    cmd_analyse: Callable,
    cmd_build: Callable,
    cmd_scaffold: Callable,
    cmd_status: Callable,
    cmd_logs: Callable,
    cmd_deploy: Callable,
) -> None:
    parser = subparsers.add_parser("builder", help="Project builder and monorepo manager")
    sub = parser.add_subparsers(dest="builder_command", required=True)

    list_parser = sub.add_parser("list", help="List discovered projects")
    list_parser.set_defaults(func=cmd_list)

    analyse_parser = sub.add_parser("analyse", help="Analyse a project")
    analyse_parser.add_argument("name", help="Project name or id")
    analyse_parser.set_defaults(func=cmd_analyse)

    build_parser = sub.add_parser("build", help="Run a build job")
    build_parser.add_argument("name", help="Project name or id")
    build_parser.add_argument("instruction", help="Natural language instruction")
    build_parser.set_defaults(func=cmd_build)

    scaffold_parser = sub.add_parser("scaffold", help="Scaffold a new project")
    scaffold_parser.add_argument("template", help="Template name")
    scaffold_parser.add_argument("name", help="Project name")
    scaffold_parser.add_argument("--path", default="/tmp/keprix-scaffolds", help="Parent directory")
    scaffold_parser.set_defaults(func=cmd_scaffold)

    status_parser = sub.add_parser("status", help="Job status")
    status_parser.add_argument("job_id", help="Build job id")
    status_parser.set_defaults(func=cmd_status)

    logs_parser = sub.add_parser("logs", help="Job logs")
    logs_parser.add_argument("job_id", help="Build job id")
    logs_parser.set_defaults(func=cmd_logs)

    deploy_parser = sub.add_parser("deploy", help="Deploy project to LAMPP or Docker")
    deploy_parser.add_argument("name", help="Project name or id")
    deploy_parser.add_argument("--target", choices=["lampp", "docker"], default="lampp")
    deploy_parser.set_defaults(func=cmd_deploy)
