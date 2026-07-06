"""``keprix agent-app`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_agent_app_parser(
    subparsers,
    *,
    cmd_list: Callable,
    cmd_validate: Callable,
    cmd_install: Callable,
    cmd_run: Callable,
    cmd_eval: Callable,
    cmd_bundle: Callable,
    cmd_create: Callable,
    cmd_catalog_list: Callable,
) -> None:
    parser = subparsers.add_parser(
        "agent-app",
        help="Portable agent apps: validate, run, eval, and bundle",
        description="Google ADK-style agent app lifecycle commands.",
    )
    app_sub = parser.add_subparsers(dest="agent_app_command", required=True)

    list_parser = app_sub.add_parser("list", help="List installed agent apps")
    list_parser.set_defaults(func=cmd_list)

    create_parser = app_sub.add_parser("create", help="Scaffold a new agent app folder")
    create_parser.add_argument("name", help="App name (slugified for manifest name)")
    create_parser.add_argument(
        "path",
        nargs="?",
        help="Destination directory (default: ./<name>)",
    )
    create_parser.add_argument(
        "--template",
        default="agent",
        choices=["agent", "python"],
        help="Scaffold template (default: agent)",
    )
    create_parser.add_argument("--force", action="store_true", help="Overwrite non-empty destination")
    create_parser.set_defaults(func=cmd_create)

    catalog_parser = app_sub.add_parser("catalog", help="Marketplace catalog commands")
    catalog_sub = catalog_parser.add_subparsers(dest="agent_app_catalog_command", required=True)
    catalog_list_parser = catalog_sub.add_parser("list", help="List catalog templates")
    catalog_list_parser.set_defaults(func=cmd_catalog_list)

    validate_parser = app_sub.add_parser("validate", help="Validate an agent app folder")
    validate_parser.add_argument("path", help="Path to agent app directory")
    validate_parser.set_defaults(func=cmd_validate)

    install_parser = app_sub.add_parser("install", help="Validate and install an agent app")
    install_parser.add_argument("path", help="Path to agent app directory")
    install_parser.set_defaults(func=cmd_install)

    run_parser = app_sub.add_parser("run", help="Run an agent app locally")
    run_parser.add_argument("path", help="Path to agent app directory")
    run_parser.add_argument("--input", default="", help="Input text for the agent")
    run_parser.set_defaults(func=cmd_run)

    eval_parser = app_sub.add_parser("eval", help="Run bundled eval suite")
    eval_parser.add_argument("path", help="Path to agent app directory")
    eval_parser.set_defaults(func=cmd_eval)

    bundle_parser = app_sub.add_parser("bundle", help="Build deployment bundle zip")
    bundle_parser.add_argument("path", help="Path to agent app directory")
    bundle_parser.add_argument("-o", "--output", help="Output zip path")
    bundle_parser.add_argument(
        "--target",
        default="local",
        choices=["local", "hub", "docker", "workspace"],
        help="Bundle target profile",
    )
    bundle_parser.set_defaults(func=cmd_bundle)
