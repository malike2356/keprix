"""``keprix readiness`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_readiness_parser(subparsers, *, cmd_readiness: Callable) -> None:
    parser = subparsers.add_parser(
        "readiness",
        help="Market, upgrade, and recovery readiness report",
        description=(
            "Run the same readiness gates as Admin > Readiness. "
            "Statuses: pass, warn, fail, unknown. Donation never blocks readiness."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    parser.add_argument(
        "--target",
        metavar="VERSION",
        default=None,
        help="Upgrade target version to check package installability (keprix==VERSION)",
    )
    parser.add_argument(
        "--category",
        choices=["market", "upgrade", "recovery", "all"],
        default="all",
        help="Filter checks by category",
    )
    parser.set_defaults(func=cmd_readiness)
