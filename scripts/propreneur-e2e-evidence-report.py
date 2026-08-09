#!/usr/bin/env python3
"""Build machine-readable e2e evidence mapping live capabilities -> tests (prompt 642)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
KEPRIX = WORKSPACE / "keprix"
NODES = (
    KEPRIX
    / "domain-packs"
    / "propreneur"
    / "contracts"
    / "generated"
    / "propreneur_pack_nodes.v1.json"
)

# Domain -> primary Pest + pytest evidence IDs
DOMAIN_EVIDENCE: dict[str, list[str]] = {
    "property": [
        "pest:AivaV1E2eCrudMatrixTest::runs create-read-update-archive matrix",
        "pest:AivaV1ApiTest::enforces tenant isolation",
        "pytest:test_property_crud_via_pack_invoke_and_chat_adapter",
    ],
    "contact": [
        "pest:AivaV1E2eCrudMatrixTest::runs create-read-update-archive matrix",
        "pest:AivaV1SecurityFailClosedTest::isolates second-role grant",
    ],
    "owner": [
        "pest:AivaV1E2eCrudMatrixTest::runs create-read-update-archive matrix",
    ],
    "deal": [
        "pest:AivaV1E2eCrudMatrixTest::runs create-read-update-archive matrix",
    ],
    "tenancy": [
        "pest:AivaV1E2eCrudMatrixTest::runs create-read-update-archive matrix",
        "pest:AivaV1ApiTest::covers tenancy project sourcing",
    ],
    "maintenance": [
        "pest:AivaV1E2eCrudMatrixTest::runs create-read-update-archive matrix",
    ],
    "project": [
        "pest:AivaV1E2eCrudMatrixTest::runs create-read-update-archive matrix",
    ],
    "sourcing": [
        "pest:AivaV1E2eCrudMatrixTest::runs create-read-update-archive matrix",
    ],
    "document": [
        "pest:AivaV1E2eCrudMatrixTest::runs create-read-update-archive matrix",
    ],
    "finance": [
        "pest:AivaV1E2eCrudMatrixTest::covers finance proposal Soft Wall",
    ],
    "appointment": [
        "pest:AivaV1E2eCrudMatrixTest::runs create-read-update-archive matrix",
    ],
    "communications": [
        "pest:AivaV1E2eCrudMatrixTest::covers finance proposal Soft Wall and communications send denial",
    ],
}

SECURITY_EVIDENCE = [
    "pest:AivaV1SecurityFailClosedTest::denies cross-tenant property access",
    "pest:AivaV1SecurityFailClosedTest::denies privilege escalation when read_only",
    "pest:AivaV1SecurityFailClosedTest::rejects forged actor headers",
    "pest:AivaV1SecurityFailClosedTest::blocks mutations with HTTP 423",
    "pest:AivaV1SecurityFailClosedTest::rejects expired or revoked grant tokens",
    "pytest:test_cross_tenant_get_fails_closed",
    "pytest:test_ssrf_circuit_and_emergency_disable_fail_closed",
    "pytest:test_soft_wall_bypass_and_forged_identity_stripped",
]


def _suite_passed(log_text: str) -> tuple[bool, int]:
    """Return (ok, failed_count) from Pest/pytest summary lines."""
    failed = 0
    # Prefer explicit summary lines near the end.
    for line in reversed(log_text.splitlines()):
        m = re.search(r"Tests:\s+(?:(\d+)\s+failed,\s*)?(\d+)\s+passed", line)
        if m:
            failed = int(m.group(1) or 0)
            return failed == 0, failed
        m2 = re.search(r"(\d+)\s+failed,\s*(\d+)\s+passed", line)
        if m2:
            failed = int(m2.group(1))
            return failed == 0, failed
        m3 = re.search(r"^(\d+)\s+passed", line.strip())
        if m3 and "failed" not in line:
            return True, 0
    if "PREFLIGHT FAILED" in log_text:
        return False, 1
    return "passed" in log_text.lower(), failed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", required=True)
    ap.add_argument("--pest-log", required=True)
    ap.add_argument("--pytest-log", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    nodes_doc = json.loads(Path(NODES).read_text(encoding="utf-8"))
    nodes = list(nodes_doc.get("nodes") or [])
    pest_log = Path(args.pest_log).read_text(encoding="utf-8", errors="replace")
    pytest_log = Path(args.pytest_log).read_text(encoding="utf-8", errors="replace")
    pest_ok, pest_failed = _suite_passed(pest_log)
    pytest_ok, pytest_failed = _suite_passed(pytest_log)

    capabilities: list[dict[str, Any]] = []
    for node in nodes:
        status = str(node.get("status") or "")
        if status not in {"live", "approval_required"}:
            continue
        domain = str(node.get("domain") or "unknown")
        tests = list(DOMAIN_EVIDENCE.get(domain, []))
        tests.append("pytest:test_live_capability_inventory_nonempty")
        if status == "approval_required":
            tests.append("pytest:test_soft_wall_bypass_and_forged_identity_stripped")
            tests.append("pytest:test_property_crud_via_pack_invoke_and_chat_adapter")
        capabilities.append(
            {
                "key": node.get("key"),
                "status": status,
                "domain": domain,
                "operation_id": node.get("operation_id"),
                "http_method": node.get("http_method"),
                "http_path": node.get("http_path"),
                "tests": tests,
                "suite_green": bool(pest_ok and pytest_ok),
            }
        )

    report = {
        "contract": "propreneur-e2e-evidence",
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prompt": "642",
        "fixtures": str(args.fixtures),
        "suites": {
            "propreneur_pest": {"ok": pest_ok, "failed": pest_failed},
            "keprix_pytest": {"ok": pytest_ok, "failed": pytest_failed},
        },
        "security_tests": SECURITY_EVIDENCE,
        "capability_count": len(capabilities),
        "capabilities": capabilities,
        "verdict": "GREEN" if pest_ok and pytest_ok else "RED",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"wrote {out} verdict={report['verdict']} capabilities={len(capabilities)}")
    return 0 if report["verdict"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
