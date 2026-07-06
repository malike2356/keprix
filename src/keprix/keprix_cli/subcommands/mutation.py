"""``keprix mutation`` subcommand parser (Prompt 151)."""

from __future__ import annotations

from typing import Callable


def build_mutation_parser(
    subparsers,
    *,
    cmd_list: Callable,
    cmd_approve: Callable,
    cmd_reject: Callable,
    cmd_rollback: Callable,
    cmd_synthesize: Callable,
    cmd_stats: Callable,
    cmd_code_request: Callable | None = None,
    cmd_code_list: Callable | None = None,
    cmd_code_diff: Callable | None = None,
    cmd_code_approve: Callable | None = None,
    cmd_code_reject: Callable | None = None,
    cmd_code_rollback: Callable | None = None,
) -> None:
    mutation_parser = subparsers.add_parser(
        "mutation",
        help="Manage synthesized tools and mutation queue",
        description="List, approve, reject, rollback, and manually synthesize mutation tools.",
    )
    mutation_sub = mutation_parser.add_subparsers(dest="mutation_command", required=True)

    list_parser = mutation_sub.add_parser("list", help="List mutation records")
    list_parser.add_argument("--status", default=None, help="Filter by status")
    list_parser.add_argument("--tier", default=None, help="Filter by tier")
    list_parser.set_defaults(func=cmd_list)

    approve_parser = mutation_sub.add_parser("approve", help="Approve a staged mutation")
    approve_parser.add_argument("mutation_id", help="Mutation record id")
    approve_parser.set_defaults(func=cmd_approve)

    reject_parser = mutation_sub.add_parser("reject", help="Reject a staged mutation")
    reject_parser.add_argument("mutation_id", help="Mutation record id")
    reject_parser.add_argument("--reason", default="", help="Rejection reason")
    reject_parser.set_defaults(func=cmd_reject)

    rollback_parser = mutation_sub.add_parser("rollback", help="Rollback an approved tool mutation")
    rollback_parser.add_argument("mutation_id", help="Mutation record id")
    rollback_parser.set_defaults(func=cmd_rollback)

    synthesize_parser = mutation_sub.add_parser("synthesize", help="Manually synthesize a tool")
    synthesize_parser.add_argument("--name", required=True, help="Tool name")
    synthesize_parser.add_argument("--description", required=True, help="Tool description")
    synthesize_parser.set_defaults(func=cmd_synthesize)

    stats_parser = mutation_sub.add_parser("stats", help="Show mutation counts by tier and status")
    stats_parser.set_defaults(func=cmd_stats)

    if cmd_code_request is not None:
        code_parser = mutation_sub.add_parser("code", help="Scoped self-coding mutations")
        code_sub = code_parser.add_subparsers(dest="code_command", required=True)

        code_request = code_sub.add_parser("request", help="Request a scoped code mutation")
        code_request.add_argument("--task", required=True, help="Natural language task")
        code_request.add_argument("--target-dir", default="src/keprix/tools/", help="Allowed target directory")
        code_request.set_defaults(func=cmd_code_request)

        code_list = code_sub.add_parser("list", help="List code mutations")
        code_list.add_argument("--status", default=None, help="Filter by status")
        code_list.set_defaults(func=cmd_code_list)

        code_diff = code_sub.add_parser("diff", help="Show code mutation diff")
        code_diff.add_argument("mutation_id", help="Mutation record id")
        code_diff.set_defaults(func=cmd_code_diff)

        code_approve = code_sub.add_parser("approve", help="Approve and merge a code mutation")
        code_approve.add_argument("mutation_id", help="Mutation record id")
        code_approve.set_defaults(func=cmd_code_approve)

        code_reject = code_sub.add_parser("reject", help="Reject a code mutation")
        code_reject.add_argument("mutation_id", help="Mutation record id")
        code_reject.add_argument("--reason", default="", help="Rejection reason")
        code_reject.set_defaults(func=cmd_code_reject)

        code_rollback = code_sub.add_parser("rollback", help="Rollback a merged code mutation")
        code_rollback.add_argument("mutation_id", help="Mutation record id")
        code_rollback.set_defaults(func=cmd_code_rollback)
