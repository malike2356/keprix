"""Eval runner for the TypeScript SDK (lifecycle trace format)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.agent_apps.lifecycle import LifecycleEvent, LifecycleTrace


def _trace(
    *,
    trace_id: str,
    app_name: str,
    event: LifecycleEvent,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return LifecycleTrace(
        trace_id=trace_id,
        app_name=app_name,
        event=event,
        payload=payload,
    ).to_dict()


def run_eval_suite(
    *,
    suite_name: str,
    cases: list[dict[str, Any]],
    runner: Any | None = None,
) -> dict[str, Any]:
    """Run eval cases and emit lifecycle-compatible traces."""
    trace_id = str(uuid.uuid4())
    app_name = suite_name or "typescript-sdk"
    traces: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    traces.append(
        _trace(
            trace_id=trace_id,
            app_name=app_name,
            event=LifecycleEvent.BEFORE_RUN,
            payload={"case_count": len(cases)},
        )
    )

    passed = 0
    for case in cases:
        name = str(case.get("name") or "unnamed")
        input_text = str(case.get("input") or "")
        expect_contains = str(case.get("expect_contains") or "")
        expect_equals = case.get("expect_equals")

        if runner is not None:
            output = str(runner(input_text))
        else:
            output = input_text.strip()

        ok = True
        if expect_contains:
            ok = expect_contains in output
        elif expect_equals is not None:
            ok = output == str(expect_equals)

        if ok:
            passed += 1

        case_result = {
            "name": name,
            "passed": ok,
            "input": input_text,
            "output": output,
        }
        results.append(case_result)
        traces.append(
            _trace(
                trace_id=trace_id,
                app_name=app_name,
                event=LifecycleEvent.AFTER_RUN,
                payload={"case": name, "passed": ok, "output": output},
            )
        )

    success = passed == len(results) and len(results) > 0
    report = {
        "suite": suite_name,
        "trace_id": trace_id,
        "passed": passed,
        "total": len(results),
        "success": success,
        "cases": results,
        "traces": traces,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    traces.append(
        _trace(
            trace_id=trace_id,
            app_name=app_name,
            event=LifecycleEvent.ON_ARTIFACT_CREATED,
            payload={"artifact": "eval_report", "success": success},
        )
    )
    report["traces"] = traces
    return report
