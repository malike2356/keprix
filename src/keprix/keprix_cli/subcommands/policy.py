"""``keprix policy`` subcommand parser (Prompt 297)."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_policy_parser(subparsers: _SubParsersAction, *, cmd_policy: Callable) -> None:
    parser = subparsers.add_parser(
        "policy",
        help="Show or set operator-owned policy profiles",
    )
    sub = parser.add_subparsers(dest="policy_command", required=True)

    show = sub.add_parser("show", help="Show resolved operator policy")
    show.add_argument("--product", default="", help="Product id")
    show.add_argument("--workspace", default="default", help="Workspace id")
    show.set_defaults(func=cmd_policy)

    set_p = sub.add_parser("set", help="Set operator policy profile")
    set_p.add_argument(
        "--profile",
        required=True,
        choices=["strict", "standard", "permissive"],
        help="Policy profile",
    )
    set_p.add_argument("--product", default="", help="Product id (optional)")
    set_p.add_argument("--workspace", default="default", help="Workspace id")
    set_p.set_defaults(func=cmd_policy)
