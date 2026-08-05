"""CLI handlers for ``keprix scout``."""

from __future__ import annotations

import json

from keprix.integrations.scout_production import (
    run_async,
    scout_health_payload,
    scout_ping,
    scout_test_command,
    scout_test_signal,
)
from keprix.security.product_policy import apply_product_policy
from keprix.security.scout_control import block_session, quarantine_tool, set_egress_force_blocked
from keprix.security.scout_metrics import product_metrics


def cmd_scout(args) -> int:
    command = args.scout_command
    if command == "ping":
        payload = run_async(scout_ping())
    elif command == "test-signal":
        payload = run_async(scout_test_signal())
    elif command == "test-command":
        payload = run_async(scout_test_command())
    elif command == "status":
        payload = run_async(scout_health_payload())
    elif command == "integration-test":
        payload = run_async(_integration_test())
    elif command == "signals":
        product = args.product
        metrics = product_metrics(product)
        payload = {"product": product, "metrics": metrics}
    elif command == "suspend":
        block_session(args.session)
        payload = {"ok": True, "session": args.session, "product": args.product}
    elif command == "quarantine":
        quarantine_tool(args.tool)
        payload = {"ok": True, "tool": args.tool, "product": args.product}
    elif command == "block-egress":
        set_egress_force_blocked(True)
        payload = {"ok": True, "egress_blocked": True, "product": args.product}
    elif command == "set-sandbox":
        record = apply_product_policy(
            args.product,
            {"sandbox": {"mode": args.mode}},
            updated_by="scout_cli",
        )
        payload = {"ok": True, "policy": record}
    else:
        print(json.dumps({"error": f"unknown scout command: {command}"}))
        return 2

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
    else:
        _print_human(command, payload)
    return 0 if payload.get("ok", True) else 1


async def _integration_test() -> dict:
    ping = await scout_ping()
    signal = await scout_test_signal()
    command = await scout_test_command()
    ok = bool(ping.get("ok") or "disabled" in str(ping.get("reason", ""))) and bool(
        signal.get("ok") or "disabled" in str(signal.get("reason", ""))
    ) and bool(command.get("ok"))
    return {
        "ok": ok,
        "ping": ping,
        "test_signal": signal,
        "test_command": command,
    }


def _print_human(command: str, payload: dict) -> None:
    if command == "ping":
        if payload.get("ok"):
            print(
                f"Scout reachable. Agent ID: {payload.get('agent_id')} "
                f"({payload.get('latency_ms')}ms)"
            )
        else:
            print(f"Scout unreachable: {payload.get('error') or payload.get('reason')}")
        return
    if command == "test-signal":
        if payload.get("ok"):
            print(f"Test signal sent. Flush latency: {payload.get('latency_ms')}ms")
        else:
            print(f"Test signal failed: {payload.get('reason', 'flush did not complete')}")
        return
    if command == "test-command":
        if payload.get("ok"):
            print(f"Test command handled. Latency: {payload.get('latency_ms')}ms")
        else:
            print(f"Test command failed: {payload.get('result')}")
        return
    if command == "integration-test":
        print(f"Scout integration test: {'PASS' if payload.get('ok') else 'FAIL'}")
        return
    if command == "signals":
        print(json.dumps(payload, indent=2))
        return
    if command in {"suspend", "quarantine", "block-egress", "set-sandbox"}:
        print(json.dumps(payload, indent=2))
        return
    if command == "status":
        print("Scout integration status:")
        for key, value in payload.items():
            print(f"  {key}: {value}")
