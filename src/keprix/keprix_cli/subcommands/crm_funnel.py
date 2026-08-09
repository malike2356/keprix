"""``keprix crm-funnel`` thin CLI (Prompt 627)."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_crm_funnel_parser(
    subparsers: _SubParsersAction,
    *,
    cmd_crm_funnel: Callable,
) -> None:
    parser = subparsers.add_parser(
        "crm-funnel",
        help="CRM funnel orchestrator, next-best-action, and channel journey",
    )
    sub = parser.add_subparsers(dest="crm_funnel_command", required=True)

    tick = sub.add_parser("tick", help="Run one funnel orchestrate action")
    tick.add_argument("--workspace-id", required=True)
    tick.add_argument("--trigger", required=True)
    tick.add_argument("--action", required=True)
    tick.add_argument("--subject-id", required=True)
    tick.add_argument("--subject-type", default="lead")
    tick.add_argument("--idempotency-key", default=None)
    tick.add_argument("--force", action="store_true")
    tick.add_argument("--approval-id", default=None)
    tick.set_defaults(func=cmd_crm_funnel)

    nba = sub.add_parser("nba", help="Suggest next-best-action for a subject")
    nba.add_argument("--workspace-id", required=True)
    nba.add_argument("--subject-id", required=True)
    nba.add_argument("--subject-type", default="lead")
    nba.add_argument("--execute", action="store_true")
    nba.add_argument("--force", action="store_true")
    nba.add_argument("--approval-id", default=None)
    nba.set_defaults(func=cmd_crm_funnel)

    journey = sub.add_parser("journey", help="Run or show channel journey status")
    journey.add_argument("--workspace-id", required=True)
    journey.add_argument("--file", default=None, help="Spreadsheet path to ingest")
    journey.add_argument("--channel", default="cli")
    journey.add_argument("--list-name", default=None)
    journey.add_argument("--status-only", action="store_true")
    journey.add_argument("--force", action="store_true")
    journey.add_argument("--approval-id", default=None)
    journey.set_defaults(func=cmd_crm_funnel)
