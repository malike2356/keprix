"""``keprix usage`` subcommand (Prompt 146)."""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from typing import Callable


def build_usage_parser(subparsers, *, cmd_usage: Callable) -> None:
    usage_parser = subparsers.add_parser(
        "usage",
        help="LLM token usage and cost analytics",
        description="Summarise persisted LLM usage events from the local usage store.",
    )
    usage_sub = usage_parser.add_subparsers(dest="usage_command", required=True)

    summary_parser = usage_sub.add_parser("summary", help="Show usage summary")
    summary_parser.add_argument("--days", type=int, default=30)
    summary_parser.set_defaults(usage_action="summary")

    breakdown_parser = usage_sub.add_parser("breakdown", help="Break down usage by dimension")
    breakdown_parser.add_argument("dimension", choices=["models", "providers", "channels", "users"])
    breakdown_parser.add_argument("--days", type=int, default=30)
    breakdown_parser.set_defaults(usage_action="breakdown")

    export_parser = usage_sub.add_parser("export", help="Export usage events to CSV")
    export_parser.add_argument("--output", "-o", required=True)
    export_parser.add_argument("--days", type=int, default=90)
    export_parser.set_defaults(usage_action="export")

    usage_parser.set_defaults(func=cmd_usage)


async def _run_summary(days: int) -> int:
    from keprix.usage.analytics import get_llm_usage_analytics
    from keprix.usage.filters import UsageQueryFilters

    summary = await get_llm_usage_analytics().summary(UsageQueryFilters(days=days))
    print(f"Period: {summary['period_days']} days")
    print(f"Requests: {summary['request_count']}")
    print(f"Tokens: {summary['total_tokens']:,}")
    print(f"Cost USD: {summary['total_cost_usd']:.4f}")
    return 0


async def _run_breakdown(dimension: str, days: int) -> int:
    from keprix.usage.analytics import get_llm_usage_analytics
    from keprix.usage.filters import UsageQueryFilters

    dim = dimension.rstrip("s")
    rows = await get_llm_usage_analytics().breakdown(UsageQueryFilters(days=days), dimension=dim)  # type: ignore[arg-type]
    for row in rows:
        print(
            f"{row['label']}: {row['total_tokens']:,} tokens, "
            f"${row['total_cost_usd']:.4f} ({row['share_percent']:.1f}%)"
        )
    return 0


async def _run_export(output: str, days: int) -> int:
    from keprix.usage.filters import UsageQueryFilters
    from keprix.usage.store import get_llm_usage_store

    filters = UsageQueryFilters(days=days)
    with open(output, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "recorded_at",
                "user_id",
                "channel",
                "provider",
                "model",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "cost_usd",
                "cost_status",
                "session_id",
                "run_id",
            ]
        )
        for row in get_llm_usage_store().iter_export_rows_sync(filters):
            writer.writerow(row)
    print(f"Wrote export to {output}")
    return 0


def cmd_usage(args: argparse.Namespace) -> int:
    action = getattr(args, "usage_action", None)
    if action == "summary":
        return asyncio.run(_run_summary(args.days))
    if action == "breakdown":
        return asyncio.run(_run_breakdown(args.dimension, args.days))
    if action == "export":
        return asyncio.run(_run_export(args.output, args.days))
    print("Unknown usage action", file=sys.stderr)
    return 2
