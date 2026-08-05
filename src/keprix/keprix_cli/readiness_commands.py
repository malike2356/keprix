"""Handlers for ``keprix readiness``."""

from __future__ import annotations

import json
import sys
from typing import Any


def cmd_readiness(args: Any) -> int:
    from keprix.readiness.service import build_report

    report = build_report(target_version=getattr(args, "target", None))
    category = getattr(args, "category", "all") or "all"
    checks = report.checks
    if category != "all":
        checks = [c for c in checks if c.category == category]
        report.checks = checks
        from keprix.readiness.models import count_statuses, rollup

        report.counts = count_statuses(checks)
        if category == "market":
            report.market = rollup([c.status for c in checks])
            report.overall = report.market
        elif category == "upgrade":
            report.upgrade = rollup([c.status for c in checks])
            report.overall = report.upgrade
        elif category == "recovery":
            report.recovery = rollup([c.status for c in checks])
            report.overall = report.recovery

    payload = report.to_dict()
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
    else:
        print(f"Overall: {report.overall}")
        print(f"Market: {report.market} | Upgrade: {report.upgrade} | Recovery: {report.recovery}")
        print(f"Counts: {report.counts}")
        for note in report.notes:
            print(f"Note: {note}")
        print("")
        for check in checks:
            fix = f" -> {check.fix_path}" if check.fix_path else ""
            print(f"[{check.status.upper():7}] {check.category}/{check.id}: {check.summary}{fix}")

    if report.overall == "fail":
        return 2
    if report.overall == "warn":
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    from keprix.keprix_cli.subcommands.readiness import build_readiness_parser

    parser = argparse.ArgumentParser(prog="keprix readiness")
    sub = parser.add_subparsers()
    # Allow direct invocation of handler in tests
    ns = argparse.Namespace(json=False, target=None, category="all")
    if argv:
        # minimal parse
        if "--json" in argv:
            ns.json = True
        if "--target" in argv:
            i = argv.index("--target")
            if i + 1 < len(argv):
                ns.target = argv[i + 1]
    return cmd_readiness(ns)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
