"""keprix tools acl-lint: validate ACL configuration for conflicts and unknown tools.

Checks:
  1. Tools in allowed_tools that are not installed (unknown tool names)
  2. Patterns in denied_tools that also appear in allowed_tools (shadowed allow)
  3. Products with an empty allowed_tools that are not the base product

Usage:
    keprix tools acl-lint <product_id>
    keprix tools acl-lint --all
    keprix tools acl-lint aiva --strict
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

from keprix.security.tool_acl import ACLDecision, ToolACL, get_tool_acl


@dataclass
class LintIssue:
    severity: str    # "error" | "warning"
    product_id: str
    pattern: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.product_id}: {self.pattern!r} - {self.message}"


@dataclass
class LintResult:
    product_id: str
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == "warning" for i in self.issues)


def lint_product(
    product_id: str,
    acl: ToolACL,
    known_tools: list[str],
    strict: bool = False,
) -> LintResult:
    """Check a single product's ACL config for issues.

    Args:
        product_id: The product to lint.
        acl: The ToolACL instance to inspect.
        known_tools: List of all currently installed tool names.
        strict: If True, unknown tools in allowed_tools are errors (not warnings).

    Returns:
        LintResult with any issues found.
    """
    result = LintResult(product_id=product_id)
    snap = acl.snapshot()

    if product_id not in snap:
        if product_id != acl.BASE_PRODUCT:
            result.issues.append(LintIssue(
                severity="error",
                product_id=product_id,
                pattern="",
                message="product is not registered in the ACL (no manifest found)",
            ))
        return result

    config = snap[product_id]
    allowed = config["allowed_tools"]
    denied = config["denied_tools"]

    # Empty allowlist for non-base products - all tools denied
    if not allowed and product_id != acl.BASE_PRODUCT:
        result.issues.append(LintIssue(
            severity="warning",
            product_id=product_id,
            pattern="",
            message="allowed_tools is empty; all tools will be denied for this product",
        ))

    known_set = set(known_tools)

    # Check for patterns that reference tools not in the installed catalog.
    # Wildcard patterns ("*", "category:*") are excluded from this check.
    for pattern in allowed:
        if "*" in pattern:
            continue
        if pattern not in known_set:
            sev = "error" if strict else "warning"
            result.issues.append(LintIssue(
                severity=sev,
                product_id=product_id,
                pattern=pattern,
                message=f"tool '{pattern}' in allowed_tools is not installed",
            ))

    for pattern in denied:
        if "*" in pattern:
            continue
        if pattern not in known_set:
            sev = "error" if strict else "warning"
            result.issues.append(LintIssue(
                severity=sev,
                product_id=product_id,
                pattern=pattern,
                message=f"tool '{pattern}' in denied_tools is not installed",
            ))

    # Detect conflict: same exact pattern in both lists
    allowed_set = set(allowed)
    denied_set = set(denied)
    conflicts = allowed_set & denied_set
    for pattern in conflicts:
        result.issues.append(LintIssue(
            severity="error",
            product_id=product_id,
            pattern=pattern,
            message="pattern appears in both allowed_tools and denied_tools (deny wins, allow is dead)",
        ))

    # Warn if a wildcard deny shadows a wildcard allow
    if "*" in denied and "*" in allowed:
        result.issues.append(LintIssue(
            severity="warning",
            product_id=product_id,
            pattern="*",
            message="'*' in denied_tools shadows the '*' in allowed_tools; no tools will be accessible",
        ))

    return result


def run_lint(
    product_ids: list[str],
    acl: ToolACL | None = None,
    known_tools: list[str] | None = None,
    strict: bool = False,
) -> list[LintResult]:
    """Run lint for all specified products and return results."""
    from keprix_cli.acl_check import _EXAMPLE_TOOLS

    acl = acl or get_tool_acl()
    catalog = known_tools or _EXAMPLE_TOOLS
    results = []

    for pid in product_ids:
        result = lint_product(pid, acl, catalog, strict=strict)
        results.append(result)

    return results


def print_lint_results(results: list[LintResult], color: bool = True) -> int:
    """Print lint results. Returns 1 if any errors, 0 if clean."""
    RED = "\033[31m" if color else ""
    YELLOW = "\033[33m" if color else ""
    GREEN = "\033[32m" if color else ""
    RESET = "\033[0m" if color else ""

    total_errors = 0
    total_warnings = 0

    for result in results:
        if not result.issues:
            print(f"{GREEN}OK{RESET} {result.product_id}: no issues found")
            continue

        for issue in result.issues:
            if issue.severity == "error":
                total_errors += 1
                prefix = f"{RED}ERROR{RESET}"
            else:
                total_warnings += 1
                prefix = f"{YELLOW}WARN{RESET}"
            print(f"  {prefix} [{result.product_id}] {issue.message}")
            if issue.pattern:
                print(f"         pattern: {issue.pattern!r}")

    print()
    if total_errors == 0 and total_warnings == 0:
        print(f"{GREEN}Lint passed: no issues across {len(results)} product(s).{RESET}")
    else:
        print(f"Lint complete: {total_errors} error(s), {total_warnings} warning(s) across {len(results)} product(s).")

    return 1 if total_errors > 0 else 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for `keprix tools acl-lint`."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="keprix tools acl-lint",
        description="Validate ACL configs for unknown tools and conflicts.",
    )
    parser.add_argument(
        "product_ids",
        nargs="*",
        help="Product IDs to lint (omit to lint all registered products)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat unknown tools in allowed_tools as errors (default: warnings)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color output",
    )
    args = parser.parse_args(argv)

    acl = get_tool_acl()
    product_ids = args.product_ids or acl.list_registered_products()
    if not product_ids:
        print("No products registered. Load ACL config first.")
        return 0

    results = run_lint(product_ids, acl=acl, strict=args.strict)
    return print_lint_results(results, color=not args.no_color)


if __name__ == "__main__":
    sys.exit(main())
