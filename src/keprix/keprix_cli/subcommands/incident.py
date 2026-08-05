"""``keprix incident`` subcommand parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_incident_parser(subparsers: _SubParsersAction, *, cmd_incident: Callable) -> None:
    parser = subparsers.add_parser(
        "incident",
        help="Incident response commands",
        description="Declare incidents, capture snapshots, and run containment actions.",
    )
    sub = parser.add_subparsers(dest="incident_command", required=True)

    declare = sub.add_parser("declare", help="Declare a security incident")
    declare.add_argument("--level", required=True, help="info|warning|critical|emergency")
    declare.add_argument("--reason", required=True)
    declare.add_argument("--product")
    declare.add_argument("--session")
    declare.add_argument("--json", action="store_true")
    declare.set_defaults(func=cmd_incident)

    snapshot = sub.add_parser("snapshot", help="Capture forensic snapshot")
    snapshot.add_argument("--session")
    snapshot.add_argument("--product")
    snapshot.add_argument("--reason", default="incident_snapshot")
    snapshot.add_argument("--json", action="store_true")
    snapshot.set_defaults(func=cmd_incident)

    rotate = sub.add_parser("rotate-creds", help="Request credential rotation")
    rotate.add_argument("--product", default="all")
    rotate.add_argument("--json", action="store_true")
    rotate.set_defaults(func=cmd_incident)

    sub.add_parser("seal-vault", help="Seal credential vault").set_defaults(func=cmd_incident)

    lockdown = sub.add_parser("lockdown", help="Full product lockdown")
    lockdown.add_argument("--product", required=True)
    lockdown.add_argument("--reason", default="incident_lockdown")
    lockdown.add_argument("--json", action="store_true")
    lockdown.set_defaults(func=cmd_incident)

    postmortem = sub.add_parser("post-mortem", help="Render post-mortem template for incident")
    postmortem.add_argument("incident_id")
    postmortem.set_defaults(func=cmd_incident)

    listing = sub.add_parser("list", help="List active incidents")
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(func=cmd_incident)
