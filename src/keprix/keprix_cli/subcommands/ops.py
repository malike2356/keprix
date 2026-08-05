"""``keprix ops`` subcommand parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_ops_parser(subparsers: _SubParsersAction, *, cmd_ops: Callable) -> None:
    parser = subparsers.add_parser(
        "ops",
        help="Security operations runbook and reports",
        description="Daily, weekly, and monthly security operations tasks.",
    )
    sub = parser.add_subparsers(dest="ops_command", required=True)

    daily = sub.add_parser("daily-check", help="Run the daily security runbook")
    daily.add_argument("--json", action="store_true")
    daily.set_defaults(func=cmd_ops)

    report = sub.add_parser("report", help="Generate security operations report")
    report.add_argument("--24h", dest="period_24h", action="store_true")
    report.add_argument("--weekly", action="store_true")
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=cmd_ops)

    sub.add_parser("compliance", help="Check per-product policy compliance").set_defaults(func=cmd_ops)

    sync = sub.add_parser("compliance-sync", help="Sync compliance evidence")
    sync.add_argument("--full", action="store_true")
    sync.add_argument("--json", action="store_true")
    sync.set_defaults(func=cmd_ops)

    sub.add_parser("policy-review", help="Review policy effectiveness").set_defaults(func=cmd_ops)

    sub.add_parser("capacity", help="Report storage and ops capacity headroom").set_defaults(func=cmd_ops)

    drill = sub.add_parser("drill", help="Run incident response drill")
    drill.add_argument("--level", default="l3", help="Drill level: l3 or l4")
    drill.add_argument("--json", action="store_true")
    drill.set_defaults(func=cmd_ops)

    cron = sub.add_parser("cron-install", help="Print cron snippets for automated runbooks")
    cron.set_defaults(func=cmd_ops)
