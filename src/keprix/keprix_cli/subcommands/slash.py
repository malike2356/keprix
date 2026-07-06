"""Slash command CLI subcommand parsers."""

from __future__ import annotations

from typing import Callable


def build_slash_parser(subparsers, *, cmd_list: Callable, cmd_run: Callable) -> None:
    slash_parser = subparsers.add_parser(
        "slash",
        help="List and run slash commands",
        description="Shared slash command registry for CLI and channel adapters.",
    )
    slash_sub = slash_parser.add_subparsers(dest="slash_command", required=True)

    list_parser = slash_sub.add_parser("list", help="List built-in slash commands")
    list_parser.set_defaults(func=cmd_list)

    run_parser = slash_sub.add_parser("run", help='Run a slash command, e.g. slash run "/status"')
    run_parser.add_argument("command", help="Slash command text")
    run_parser.set_defaults(func=cmd_run)
