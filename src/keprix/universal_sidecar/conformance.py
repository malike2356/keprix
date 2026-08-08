"""Basic Universal Sidecar conformance suite (KUS-02 / KUS-11 starter)."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.universal_sidecar.events import (
    get_approval_store,
    get_event_service,
    get_job_service,
    get_webhook_delivery,
)
from keprix.universal_sidecar.memory import get_memory_service
from keprix.universal_sidecar.pairing import get_pairing_store
from keprix.universal_sidecar.registry import get_project_registry
from keprix.universal_sidecar.routes import router, set_shutting_down


def reset_stores() -> None:
    get_project_registry().reset_for_tests()
    get_pairing_store().reset_for_tests()
    get_event_service().reset_for_tests()
    get_job_service().reset_for_tests()
    get_approval_store().reset_for_tests()
    get_webhook_delivery().reset_for_tests()
    get_memory_service().reset_for_tests()
    set_shutting_down(False)


def minimal_manifest(project_key: str = "demo") -> dict[str, Any]:
    return {
        "contract_version": "1.0.0",
        "project_key": project_key,
        "display_name": "Conformance Demo",
        "deployment": "local",
        "environment": "local",
        "base_url": "http://127.0.0.1:9",
        "auth": {"profile": "bearer", "vault_ref": "env:KEPRIX_DEMO_TOKEN"},
        "capabilities": [
            {"node": "summarise", "version": "1.0.0"},
            {"node": "project.read", "version": "1.0.0"},
        ],
        "egress": {"allow_loopback": True},
        "memory": {"mode": "ephemeral"},
    }


def _check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "detail": detail}


def run_conformance(*, write_report: bool = True) -> dict[str, Any]:
    """Run a basic in-process conformance suite against TestClient."""
    prev_dev = os.environ.get("KEPRIX_SIDECAR_DEV_OPEN")
    os.environ["KEPRIX_SIDECAR_DEV_OPEN"] = "1"
    checks: list[dict[str, Any]] = []
    try:
        reset_stores()
        get_project_registry().apply(minimal_manifest())

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        r = client.get("/sidecar/v1/health")
        checks.append(_check("root_health", r.status_code == 200 and r.json().get("status") == "ok"))

        r = client.get("/sidecar/v1/ready")
        checks.append(_check("root_ready", r.status_code == 200))

        pair = client.post(
            "/sidecar/v1/projects/demo/pair/code",
            json={"scopes": ["discover", "jobs", "events", "invoke:summarise", "memory:ephemeral/read", "memory:ephemeral/write"]},
        )
        checks.append(_check("pair_code", pair.status_code == 200, str(pair.status_code)))
        code = (pair.json() or {}).get("code", "")

        approve = client.post(
            "/sidecar/v1/projects/demo/pair/approve",
            json={"code": code},
        )
        checks.append(_check("pair_approve", approve.status_code == 200, str(approve.status_code)))
        token = (approve.json() or {}).get("access_token", "")
        headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": f"conf-{uuid.uuid4().hex[:8]}"}

        inv = client.post(
            "/sidecar/v1/projects/demo/invoke",
            headers=headers,
            json={"node": "summarise", "input": {"text": "hello conformance"}},
        )
        checks.append(
            _check(
                "invoke_summarise",
                inv.status_code == 200 and "summary" in (inv.json().get("output") or {}),
                str(inv.status_code),
            )
        )

        job_headers = {**headers, "Idempotency-Key": "conf-job-1"}
        job1 = client.post(
            "/sidecar/v1/projects/demo/jobs",
            headers=job_headers,
            json={"node": "summarise", "input": {"text": "job text"}, "run_inline": True},
        )
        job2 = client.post(
            "/sidecar/v1/projects/demo/jobs",
            headers=job_headers,
            json={"node": "summarise", "input": {"text": "job text"}, "run_inline": True},
        )
        j1 = (job1.json() or {}).get("job") or {}
        j2 = (job2.json() or {}).get("job") or {}
        checks.append(
            _check(
                "job_idempotency",
                job1.status_code == 200
                and job2.status_code == 200
                and j1.get("job_id") == j2.get("job_id"),
                f"{j1.get('job_id')} vs {j2.get('job_id')}",
            )
        )

        cancel_create = client.post(
            "/sidecar/v1/projects/demo/jobs",
            headers={**headers, "Idempotency-Key": "conf-job-cancel"},
            json={"node": "wait", "input": {}, "run_inline": False},
        )
        cancel_id = ((cancel_create.json() or {}).get("job") or {}).get("job_id")
        cancel = client.post(
            f"/sidecar/v1/projects/demo/jobs/{cancel_id}/cancel",
            headers=headers,
        )
        checks.append(
            _check(
                "job_cancel",
                cancel.status_code == 200
                and ((cancel.json() or {}).get("job") or {}).get("status") == "cancelled",
                str(cancel.status_code),
            )
        )

        ev_body = {
            "id": "evt-conf-1",
            "type": "demo.ping",
            "source": "conformance",
            "deployment": "local",
            "data": {"n": 1},
        }
        e1 = client.post("/sidecar/v1/projects/demo/events", headers=headers, json=ev_body)
        e2 = client.post("/sidecar/v1/projects/demo/events", headers=headers, json=ev_body)
        checks.append(
            _check(
                "event_dedupe",
                e1.status_code == 200
                and e2.status_code == 200
                and e1.json().get("duplicate") is False
                and e2.json().get("duplicate") is True,
                f"d1={e1.json().get('duplicate')} d2={e2.json().get('duplicate')}",
            )
        )

        get_memory_service().write(
            project_key="demo",
            tenant_id="t-a",
            namespace="ephemeral",
            content="secret-for-tenant-a",
            source="conformance",
        )
        get_memory_service().write(
            project_key="demo",
            tenant_id="t-b",
            namespace="ephemeral",
            content="secret-for-tenant-b",
            source="conformance",
        )
        hits_a = get_memory_service().search(project_key="demo", tenant_id="t-a", query="secret")
        hits_b = get_memory_service().search(project_key="demo", tenant_id="t-b", query="secret")
        a_ok = all("tenant-b" not in (h.get("content") or "") for h in hits_a) and any(
            "tenant-a" in (h.get("content") or "") for h in hits_a
        )
        b_ok = all("tenant-a" not in (h.get("content") or "") for h in hits_b)
        checks.append(_check("memory_cross_tenant_isolation", a_ok and b_ok))

        denied = client.post(
            "/sidecar/v1/projects/demo/invoke",
            headers=headers,
            json={"node": "shell.exec", "input": {"cmd": "id"}},
        )
        body = denied.json() if denied.headers.get("content-type", "").startswith("application/json") else {}
        checks.append(
            _check(
                "dangerous_node_denied",
                denied.status_code in {403, 404}
                or (isinstance(body, dict) and body.get("code") in {"denied", "unknown_node"}),
                str(denied.status_code),
            )
        )

        ok = all(c["ok"] for c in checks)
        report_path = None
        if write_report:
            fd, path = tempfile.mkstemp(prefix="kus-conformance-", suffix=".json")
            os.close(fd)
            report_path = path
            Path(path).write_text(json.dumps({"ok": ok, "checks": checks}, indent=2), encoding="utf-8")
        return {"ok": ok, "checks": checks, "report_path": report_path}
    finally:
        if prev_dev is None:
            os.environ.pop("KEPRIX_SIDECAR_DEV_OPEN", None)
        else:
            os.environ["KEPRIX_SIDECAR_DEV_OPEN"] = prev_dev
