"""Eval runner for bundled agent app tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from keprix.agent_apps.app_manifest import load_manifest
from keprix.agent_apps.local_runner import run_local


def run_eval_suite(app_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(app_dir)
    if not manifest.eval_suite:
        raise ValueError("App manifest does not define eval_suite")
    suite_path = app_dir / manifest.eval_suite
    suite = yaml.safe_load(suite_path.read_text(encoding="utf-8")) or {}
    cases = suite.get("cases") or []
    results: list[dict[str, Any]] = []
    passed = 0
    for case in cases:
        name = str(case.get("name") or "unnamed")
        input_text = str(case.get("input") or "")
        run_result = run_local(app_dir, input_text=input_text)
        output = str(run_result.get("result", {}).get("output", ""))
        expect = str(case.get("expect_contains") or "")
        ok = expect in output if expect else run_result.get("result", {}).get("status") == "ok"
        if ok:
            passed += 1
        results.append({"name": name, "passed": ok, "output": output})
    return {
        "app": manifest.name,
        "suite": manifest.eval_suite,
        "passed": passed,
        "total": len(results),
        "success": passed == len(results) and len(results) > 0,
        "cases": results,
    }
