"""CLI handlers for ``keprix ops``."""

from __future__ import annotations

import asyncio
import json

from keprix.ops.capacity import capacity_report
from keprix.ops.compliance import compliance_status, compliance_sync
from keprix.ops.drill import run_drill
from keprix.ops.policy_review import policy_review
from keprix.ops.reports import report_24h, report_weekly
from keprix.ops.runbook import RunbookExecutor, checks_to_dict


def cmd_ops(args) -> int:
    command = args.ops_command
    if command == "daily-check":
        checks = asyncio.run(RunbookExecutor().daily())
        payload = {"checks": checks_to_dict(checks), "ok": all(item.passed for item in checks)}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            _print_checks("Daily runbook", checks)
        return 0 if payload["ok"] else 1

    if command == "report":
        if getattr(args, "weekly", False):
            payload = report_weekly()
        else:
            payload = report_24h()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Security report ({payload.get('period')})")
            print(f"  Signals (24h): {payload.get('signals_24h')}")
            print(f"  Open incidents: {len(payload.get('open_incidents') or [])}")
            print(f"  Correlated attacks: {len(payload.get('correlated_attacks') or [])}")
        return 0

    if command == "compliance":
        payload = compliance_status()
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("ok") else 1

    if command == "compliance-sync":
        payload = compliance_sync(full=bool(args.full))
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Compliance sync ok={payload.get('ok')} frameworks={payload.get('frameworks')}")
        return 0 if payload.get("ok") else 1

    if command == "policy-review":
        payload = policy_review()
        print(json.dumps(payload, indent=2))
        return 0

    if command == "capacity":
        payload = capacity_report()
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("ok") else 1

    if command == "drill":
        payload = run_drill(level=args.level)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(
                f"Drill {payload.get('level')}: "
                f"{'PASS' if payload.get('ok') else 'FAIL'} "
                f"in {payload.get('elapsed_seconds')}s "
                f"(target {payload.get('target_seconds')}s)"
            )
        return 0 if payload.get("ok") else 1

    if command == "cron-install":
        print("Daily runbook (7:00 UTC):")
        print("0 7 * * * keprix ops daily-check >> /var/log/keprix-ops-daily.log 2>&1")
        print()
        print("Weekly runbook (Monday 8:00 UTC):")
        print("0 8 * * 1 keprix ops policy-review && keprix security pentest --quick >> /var/log/keprix-ops-weekly.log 2>&1")
        print()
        print("Monthly runbook (1st of month 9:00 UTC):")
        print("0 9 1 * * keprix security pentest --full && keprix scout integration-test >> /var/log/keprix-ops-monthly.log 2>&1")
        return 0

    print(json.dumps({"error": f"unknown ops command: {command}"}))
    return 2


def _print_checks(title: str, checks) -> None:
    print(title)
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"  [{status}] {check.name}: {check.details or check.result}")
