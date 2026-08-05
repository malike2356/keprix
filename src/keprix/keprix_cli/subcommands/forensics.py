"""``keprix forensics`` subcommand parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_forensics_parser(subparsers: _SubParsersAction, *, cmd_forensics: Callable) -> None:
    parser = subparsers.add_parser(
        "forensics",
        help="Forensic snapshot and chain-of-custody tools",
    )
    sub = parser.add_subparsers(dest="forensics_command", required=True)

    snapshot = sub.add_parser("snapshot", help="Capture forensic snapshot")
    snapshot.add_argument("--session")
    snapshot.add_argument("--product")
    snapshot.add_argument("--reason", default="manual")
    snapshot.add_argument("--json", action="store_true")
    snapshot.set_defaults(func=cmd_forensics)

    sub.add_parser("list", help="List forensic snapshots").set_defaults(func=cmd_forensics)

    analyze = sub.add_parser("analyze", help="Analyze snapshot with heuristics")
    analyze.add_argument("--snapshot", required=True)
    analyze.add_argument("--json", action="store_true")
    analyze.set_defaults(func=cmd_forensics)

    export = sub.add_parser("export", help="Export snapshot for legal review")
    export.add_argument("--snapshot", required=True)
    export.add_argument("--output")
    export.set_defaults(func=cmd_forensics)

    sub.add_parser("chain-verify", help="Verify forensic chain of custody").set_defaults(func=cmd_forensics)
