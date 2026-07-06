"""Self-configuration CLI subcommand parsers."""

from __future__ import annotations

from typing import Callable


def build_self_config_parsers(
    subparsers,
    *,
    cmd_configure: Callable,
    cmd_health: Callable,
    cmd_proposals: Callable,
    cmd_approve: Callable,
    cmd_reject: Callable,
    cmd_repair: Callable,
    cmd_rollback: Callable,
) -> None:
    configure_parser = subparsers.add_parser(
        "configure",
        help="Run environment discovery (first-run wizard)",
        description="Probe the environment and generate a working configuration file.",
    )
    configure_parser.set_defaults(func=cmd_configure)

    health_parser = subparsers.add_parser(
        "health",
        help="Show current component health status",
        description="Run health checks against LLM providers, Redis, Postgres, egress, and channels.",
    )
    health_parser.set_defaults(func=cmd_health)

    proposals_parser = subparsers.add_parser(
        "proposals",
        help="List pending config optimization proposals",
    )
    proposals_parser.set_defaults(func=cmd_proposals)

    approve_parser = subparsers.add_parser(
        "approve",
        help="Apply a config proposal after review",
    )
    approve_parser.add_argument("proposal_id", help="Proposal ID from `keprix proposals`")
    approve_parser.set_defaults(func=cmd_approve)

    reject_parser = subparsers.add_parser(
        "reject",
        help="Dismiss a config proposal",
    )
    reject_parser.add_argument("proposal_id", help="Proposal ID from `keprix proposals`")
    reject_parser.set_defaults(func=cmd_reject)

    repair_parser = subparsers.add_parser(
        "repair",
        help="Manually trigger auto-repair for all components",
    )
    repair_parser.set_defaults(func=cmd_repair)

    rollback_parser = subparsers.add_parser(
        "rollback",
        help="Roll back a specific env var to its previous value",
    )
    rollback_parser.add_argument("env_key", help="Environment variable key to roll back")
    rollback_parser.set_defaults(func=cmd_rollback)
