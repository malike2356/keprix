"""``keprix upstream`` subcommand parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_upstream_parser(subparsers: _SubParsersAction, *, cmd_upstream: Callable) -> None:
    parser = subparsers.add_parser(
        "upstream",
        help="Monitor Hermes upstream releases and manage feature adoption",
        description=(
            "Track Hermes Agent releases, require human approval, generate hardened "
            "Keprix prompts and work packages."
        ),
    )
    sub = parser.add_subparsers(dest="upstream_command", required=True)

    check = sub.add_parser("check", help="Check for new Hermes releases")
    check.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    check.add_argument(
        "--inventory",
        help="Path to hermes_inventory.yaml (default: ~/.keprix/upstream/)",
    )
    check.add_argument(
        "--no-enrichment",
        action="store_true",
        help="Skip CHANGELOG and GitHub compare enrichment",
    )
    check.set_defaults(func=cmd_upstream)

    listing = sub.add_parser("list", help="List tracked upstream features")
    listing.add_argument("--category", "-c", help="Filter by category")
    listing.add_argument("--status", "-s", help="Filter by adoption status")
    listing.add_argument("--pending", action="store_true", help="Only undecided features")
    listing.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    listing.add_argument("--inventory", help="Inventory YAML path override")
    listing.set_defaults(func=cmd_upstream)

    review = sub.add_parser("review", help="Show features pending human decision")
    review.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    review.add_argument("--inventory", help="Inventory YAML path override")
    review.set_defaults(func=cmd_upstream)

    decide = sub.add_parser("decide", help="Record an adoption decision for a feature")
    decide.add_argument("feature_id", help="Tracked feature id from `upstream list`")
    decide.add_argument(
        "--status",
        "-s",
        required=True,
        help="adopt | adopt_with_hardening | skip | defer | blocked | already_have",
    )
    decide.add_argument("--notes", default="", help="Decision notes")
    decide.add_argument("--by", default="operator", help="Decision actor (default: operator)")
    decide.add_argument("--equivalent", help="Keprix capability id when marking already_have")
    decide.add_argument("--inventory", help="Inventory YAML path override")
    decide.set_defaults(func=cmd_upstream)

    adopt = sub.add_parser("adopt", help="Generate an adoption prompt for an approved feature")
    adopt.add_argument("feature_id", help="Tracked feature id from `upstream list`")
    adopt.add_argument("--inventory", help="Inventory YAML path override")
    adopt.add_argument("--prompts-dir", help="Directory for generated prompt files")
    adopt.add_argument("--work-packages-dir", help="Directory for work package YAML files")
    adopt.set_defaults(func=cmd_upstream)

    complete = sub.add_parser(
        "complete",
        help="Mark an adopted feature as implemented (already_have + registry update)",
    )
    complete.add_argument("feature_id", help="Tracked feature id")
    complete.add_argument(
        "--equivalent",
        required=True,
        help="Keprix capability id to record (e.g. tools-mcp)",
    )
    complete.add_argument("--notes", default="", help="Completion notes")
    complete.add_argument("--by", default="operator", help="Actor")
    complete.add_argument("--inventory", help="Inventory YAML path override")
    complete.set_defaults(func=cmd_upstream)

    work = sub.add_parser("work-package", help="Show or regenerate work package for a feature")
    work.add_argument("feature_id", help="Tracked feature id")
    work.add_argument("--regenerate", action="store_true", help="Rewrite the work package YAML")
    work.add_argument("--inventory", help="Inventory YAML path override")
    work.add_argument("--work-packages-dir", help="Output directory override")
    work.set_defaults(func=cmd_upstream)

    diff = sub.add_parser("diff", help="Show Keprix vs Hermes feature inventory diff")
    diff.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    diff.add_argument("--inventory", help="Inventory YAML path override")
    diff.set_defaults(func=cmd_upstream)

    report = sub.add_parser("report", help="Generate upstream adoption report")
    report.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    report.add_argument("--inventory", help="Inventory YAML path override")
    report.set_defaults(func=cmd_upstream)

    cron = sub.add_parser(
        "cron-install",
        help="Print or install cron job for daily upstream checks",
    )
    cron.add_argument(
        "--install",
        action="store_true",
        help="Append the daily check to the current user crontab if missing",
    )
    cron.set_defaults(func=cmd_upstream)

    sync = sub.add_parser(
        "sync-registry",
        help="Refresh keprix_features from the capability registry into the inventory",
    )
    sync.add_argument("--inventory", help="Inventory YAML path override")
    sync.set_defaults(func=cmd_upstream)
