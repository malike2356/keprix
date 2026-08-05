"""keprix tools acl-check: print resolved ACL decisions for a product.

Usage:
    keprix tools acl-check <product_id>
    keprix tools acl-check <product_id> --tool terminal:run
    keprix tools acl-check <product_id> --format json
"""

from __future__ import annotations

import json
import sys
from typing import Any

from keprix.security.tool_acl import ACLDecision, ToolACL, get_tool_acl


# Placeholder tool catalog used when no live registry is available.
# In production, replace this with a call to the tool registry.
_EXAMPLE_TOOLS = [
    "crm:create_contact",
    "crm:list_contacts",
    "crm:delete_contact",
    "documents:read",
    "documents:write",
    "documents:delete",
    "terminal:run",
    "terminal:ssh",
    "search:web",
    "search:database",
    "email:send",
    "email:read",
    "calendar:create",
    "calendar:read",
    "code:execute",
    "code:edit",
    "memory:read",
    "memory:write",
]


def _decision_color(decision: ACLDecision) -> str:
    colors = {
        ACLDecision.ALLOWED: "\033[32m",          # green
        ACLDecision.DENIED: "\033[31m",            # red
        ACLDecision.DENIED_NOT_LISTED: "\033[33m", # yellow
        ACLDecision.UNKNOWN_PRODUCT: "\033[35m",   # magenta
    }
    return colors.get(decision, "")


RESET = "\033[0m"


def run_acl_check(
    product_id: str,
    acl: ToolACL | None = None,
    tool_filter: str | None = None,
    output_format: str = "table",
    tool_catalog: list[str] | None = None,
    color: bool = True,
) -> dict[str, Any]:
    """Resolve and print all ACL decisions for a product.

    Returns a dict of {tool_name: decision_value} for scripting.
    """
    acl = acl or get_tool_acl()
    catalog = tool_catalog or _EXAMPLE_TOOLS

    if tool_filter:
        catalog = [t for t in catalog if tool_filter in t]

    decisions = acl.resolved_tools(product_id, catalog)

    if output_format == "json":
        result = {k: v.value for k, v in decisions.items()}
        print(json.dumps(result, indent=2))
        return result

    # Table output
    col_w = max((len(t) for t in catalog), default=20) + 2
    header = f"{'TOOL':<{col_w}} DECISION"
    print(f"\nACL check for product: {product_id}")
    print("-" * (col_w + 20))
    print(header)
    print("-" * (col_w + 20))

    counts: dict[str, int] = {d.value: 0 for d in ACLDecision}

    for tool_name, decision in sorted(decisions.items()):
        counts[decision.value] = counts.get(decision.value, 0) + 1
        prefix = _decision_color(decision) if color else ""
        suffix = RESET if color else ""
        print(f"{tool_name:<{col_w}} {prefix}{decision.value}{suffix}")

    print("-" * (col_w + 20))
    summary_parts = [f"{v} {k}" for k, v in counts.items() if v > 0]
    print("Summary: " + ", ".join(summary_parts))
    print()

    return {k: v.value for k, v in decisions.items()}


def main(argv: list[str] | None = None) -> int:
    """Entry point for `keprix tools acl-check`."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="keprix tools acl-check",
        description="Print the resolved ACL decision for all tools for a product.",
    )
    parser.add_argument("product_id", help="Product ID to check (e.g. aiva, abbis)")
    parser.add_argument("--tool", help="Filter to a specific tool name or substring")
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color output",
    )
    args = parser.parse_args(argv)

    run_acl_check(
        product_id=args.product_id,
        tool_filter=args.tool,
        output_format=args.format,
        color=not args.no_color,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
