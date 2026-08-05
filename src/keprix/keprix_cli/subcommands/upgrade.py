"""``keprix upgrade`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_upgrade_parser(subparsers, *, cmd_upgrade: Callable) -> None:
    """Attach the ``upgrade`` subcommand to ``subparsers``."""
    parser = subparsers.add_parser(
        "upgrade",
        help="Safe, guided Keprix upgrades for products (check, plan, dry-run, execute)",
        description=(
            "Analyse, simulate, and perform Keprix version upgrades for a product "
            "with keprix.yaml in the current directory (or --path). "
            "Typical flow: --check, then --dry-run --to <version>, then --to <version>."
        ),
    )
    parser.add_argument(
        "--path",
        metavar="DIR",
        help="Product root containing keprix.yaml (default: search upward from cwd)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON (supported by --check and --prompt)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmations and bypass some preflight checks",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Assume yes for --prompt adoption wizards",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip pytest during --dry-run (dangerous)",
    )
    parser.add_argument(
        "--step",
        action="store_true",
        help="Show migration details in --plan output",
    )
    parser.add_argument(
        "--to",
        metavar="VERSION",
        help="Target Keprix version or 'latest'",
    )

    parser.add_argument(
        "--list-prompts",
        action="store_true",
        help="List guided feature adoption prompts",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only upgrade safety analysis",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Show step-by-step upgrade path",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Show upgrade history",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate upgrade and run product tests in a sandbox",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Undo the last successful upgrade from backup",
    )
    parser.add_argument(
        "--prompt",
        metavar="NAME",
        dest="prompt_name",
        help="Guided feature adoption (e.g. adopt-a2a, adopt-billing)",
    )
    parser.set_defaults(func=cmd_upgrade)
