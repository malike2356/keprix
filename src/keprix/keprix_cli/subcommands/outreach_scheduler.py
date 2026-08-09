"""``keprix outreach-scheduler`` thin CLI (Prompt 624)."""

from __future__ import annotations

import json
from argparse import _SubParsersAction
from collections.abc import Callable


def build_outreach_scheduler_parser(
    subparsers: _SubParsersAction,
    *,
    cmd_outreach_scheduler: Callable,
) -> None:
    parser = subparsers.add_parser(
        "outreach-scheduler",
        help="Durable outreach campaign sequence scheduler (claim-lease ticks)",
    )
    sub = parser.add_subparsers(dest="outreach_scheduler_command", required=True)

    tick = sub.add_parser("tick", help="Claim and process due enrollments")
    tick.add_argument("--workspace-id", default=None)
    tick.add_argument("--limit", type=int, default=50)
    tick.add_argument("--worker-id", default=None)
    tick.add_argument("--lease-seconds", type=int, default=60)
    tick.add_argument("--dry-run", action="store_true")
    tick.set_defaults(func=cmd_outreach_scheduler)

    health = sub.add_parser("health", help="Show scheduler queue health")
    health.add_argument("--workspace-id", default=None)
    health.set_defaults(func=cmd_outreach_scheduler)
