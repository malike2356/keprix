"""``keprix audit`` subcommand parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_audit_parser(subparsers: _SubParsersAction, *, cmd_audit: Callable) -> None:
    parser = subparsers.add_parser(
        "audit",
        help="Audit chain verification",
    )
    sub = parser.add_subparsers(dest="audit_command", required=True)
    sub.add_parser("verify", help="Verify forensic chain of custody").set_defaults(func=cmd_audit)
