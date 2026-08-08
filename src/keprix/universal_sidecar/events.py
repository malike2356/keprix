"""Events, durable jobs, webhooks, SSE helpers, idempotency (KUS-06)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
import uuid
from typing import Any, Iterator

from keprix.universal_sidecar.registry import get_project_registry

JOB_STATES = frozenset(
    {
        "queued",
        "running",
        "waiting",
        "awaiting_approval",
        "paused",
        "succeeded",
        "partially_succeeded",
        "failed",
        "cancelled",
        "expired",
        "dead_letter",
    }
)


class EventService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._inbox: dict[str, dict[str, Any]] = {}
        self._outbox: list[dict[str, Any]] = []
        self._replay: dict[str, float] = {}
        self._cursors: dict[str, list[dict[str, Any]]] = {}
        self._seq = 0

    def reset_for_tests(self) -> None:
        with self._lock:
            self._inbox.clear()
            self._outbox.clear()
            self._replay.clear()
            self._cursors.clear()
            self._seq = 0

    def _dedupe_key(self, project: str, deployment: str, event_id: str) -> str:
        return f"{project}:{deployment}:{event_id}"

    def ingest_inbound(
        self,
        *,
        project_key: str,
        envelope: dict[str, Any],
        signature: str | None = None,
        timestamp: str | None = None,
        key_id: str | None = None,
    ) -> dict[str, Any]:
        event_id = str(envelope.get("id") or "")
        if not event_id:
            raise ValueError("event id required")
        deployment = str(envelope.get("deployment") or "local")
        dedupe = self._dedupe_key(project_key, deployment, event_id)
        with self._lock:
            if dedupe in self._inbox:
                return {"duplicate": True, "event": dict(self._inbox[dedupe])}
            # Replay cache for signed deliveries
            if signature:
                body = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
                secret = os.environ.get("KEPRIX_SIDECAR_WEBHOOK_SECRET", "dev-webhook-secret")
                expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(signature, expected):
                    raise ValueError("invalid_signature")
                if timestamp:
                    try:
                        ts = float(timestamp)
                        if abs(time.time() - ts) > 300:
                            raise ValueError("timestamp_tolerance")
                    except ValueError:
                        raise
                    replay_key = f"{key_id or 'k1'}:{signature}"
                    if replay_key in self._replay:
                        raise ValueError("replay")
                    self._replay[replay_key] = time.time()
            row = {
                "id": event_id,
                "source": envelope.get("source"),
                "type": envelope.get("type"),
                "specversion": envelope.get("specversion") or "1.0",
                "project": project_key,
                "deployment": deployment,
                "environment": envelope.get("environment") or "local",
                "tenant": envelope.get("tenant") or envelope.get("tenant_id") or "",
                "subject": envelope.get("subject"),
                "time": envelope.get("time") or time.time(),
                "received": time.time(),
                "correlation": envelope.get("correlation") or envelope.get("correlation_id"),
                "sensitivity": envelope.get("sensitivity") or "internal",
                "data": envelope.get("data") or {},
                "status": "accepted",
            }
            self._inbox[dedupe] = row
            self._append_cursor(project_key, {"kind": "inbound_event", "event": row})
            return {"duplicate": False, "event": dict(row)}

    def emit_outbound(
        self,
        *,
        project_key: str,
        event_type: str,
        data: dict[str, Any],
        tenant_id: str = "",
        correlation_id: str = "",
    ) -> dict[str, Any]:
        row = {
            "id": f"evt_{uuid.uuid4().hex[:16]}",
            "source": f"keprix/sidecar/{project_key}",
            "type": event_type,
            "specversion": "1.0",
            "project": project_key,
            "tenant": tenant_id,
            "time": time.time(),
            "correlation": correlation_id,
            "data": data,
        }
        with self._lock:
            self._outbox.append(row)
            self._append_cursor(project_key, {"kind": "outbound_event", "event": row})
        return dict(row)

    def _append_cursor(self, project_key: str, item: dict[str, Any]) -> None:
        self._seq += 1
        item = {**item, "cursor": str(self._seq), "id": str(self._seq)}
        bucket = self._cursors.setdefault(project_key, [])
        bucket.append(item)
        if len(bucket) > 1000:
            del bucket[:-1000]

    def stream_events(self, project_key: str, *, cursor: str | None = None) -> Iterator[dict[str, Any]]:
        with self._lock:
            items = list(self._cursors.get(project_key) or [])
        start = 0
        if cursor:
            for i, item in enumerate(items):
                if str(item.get("cursor")) == str(cursor):
                    start = i + 1
                    break
        for item in items[start:]:
            yield item

    def snapshot(self, project_key: str) -> dict[str, Any]:
        with self._lock:
            return {
                "project": project_key,
                "cursor": str(self._seq),
                "recent": list(self._cursors.get(project_key) or [])[-50:],
            }


class JobService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._by_idem: dict[str, str] = {}
        self._fairness: dict[str, int] = {}

    def reset_for_tests(self) -> None:
        with self._lock:
            self._jobs.clear()
            self._by_idem.clear()
            self._fairness.clear()

    def create(
        self,
        *,
        project_key: str,
        node_key: str,
        input_payload: dict[str, Any],
        idempotency_key: str,
        tenant_id: str = "",
        actor_id: str = "",
        correlation_id: str = "",
    ) -> dict[str, Any]:
        if not idempotency_key:
            raise ValueError("Idempotency-Key required")
        if get_project_registry().is_killed(project_key):
            raise PermissionError("project_killed")
        if not get_project_registry().consume_budget(project_key, kind="jobs"):
            raise PermissionError("budget_exceeded")
        # Fairness: cap concurrent queued/running per project
        with self._lock:
            active = sum(
                1
                for j in self._jobs.values()
                if j["project"] == project_key and j["status"] in {"queued", "running", "waiting"}
            )
            if active >= 50:
                raise PermissionError("load_shedding")
            idem_ns = f"{project_key}:{idempotency_key}"
            if idem_ns in self._by_idem:
                prior = self._jobs[self._by_idem[idem_ns]]
                if prior.get("input") != input_payload or prior.get("node_key") != node_key:
                    raise ValueError("idempotency_conflict")
                return dict(prior)
            job_id = f"job_{uuid.uuid4().hex[:16]}"
            row = {
                "job_id": job_id,
                "project": project_key,
                "tenant_id": tenant_id,
                "actor_id": actor_id,
                "node_key": node_key,
                "status": "queued",
                "progress": 0,
                "checkpoint": None,
                "attempts": 0,
                "budget": 1,
                "next_retry": None,
                "input": input_payload,
                "idempotency_key": idempotency_key,
                "correlation_id": correlation_id,
                "result": None,
                "error": None,
                "cancel_requested": False,
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            self._jobs[job_id] = row
            self._by_idem[idem_ns] = job_id
            self._fairness[project_key] = self._fairness.get(project_key, 0) + 1
            return dict(row)

    def get(self, job_id: str, *, project_key: str, tenant_id: str = "") -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job["project"] != project_key:
                return None
            if tenant_id and job.get("tenant_id") and job["tenant_id"] != tenant_id:
                return None
            return dict(job)

    def cancel(self, job_id: str, *, project_key: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job["project"] != project_key:
                return None
            if job["status"] in {"cancelled", "succeeded", "failed", "dead_letter"}:
                return dict(job)
            job["status"] = "cancelled"
            job["cancel_requested"] = True
            job["updated_at"] = time.time()
            return dict(job)

    def run_inline(self, job_id: str, runner) -> dict[str, Any]:
        """Execute job cooperatively; quarantine late results after cancel."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise KeyError(job_id)
            if job["cancel_requested"] or job["status"] == "cancelled":
                return dict(job)
            job["status"] = "running"
            job["attempts"] += 1
            job["updated_at"] = time.time()
            snapshot = dict(job)
        try:
            result = runner(snapshot)
        except Exception as exc:
            with self._lock:
                job = self._jobs[job_id]
                if job["cancel_requested"]:
                    job["status"] = "cancelled"
                    job["error"] = "cancelled_before_result"
                else:
                    job["status"] = "failed"
                    job["error"] = str(exc)
                job["updated_at"] = time.time()
                return dict(job)
        with self._lock:
            job = self._jobs[job_id]
            if job["cancel_requested"] or job["status"] == "cancelled":
                job["status"] = "cancelled"
                job["error"] = "late_result_quarantined"
                job["result"] = None
            else:
                job["status"] = "succeeded"
                job["progress"] = 100
                job["result"] = result
                job["checkpoint"] = {"done": True}
            job["updated_at"] = time.time()
            return dict(job)


class ApprovalStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rows: dict[str, dict[str, Any]] = {}

    def reset_for_tests(self) -> None:
        with self._lock:
            self._rows.clear()

    def create(
        self,
        *,
        project_key: str,
        tenant_id: str,
        actor_id: str,
        action: str,
        input_hash: str,
        payload: dict[str, Any],
        ttl_seconds: int = 3600,
    ) -> dict[str, Any]:
        with self._lock:
            approval_id = f"apr_{uuid.uuid4().hex[:12]}"
            row = {
                "id": approval_id,
                "project": project_key,
                "tenant_id": tenant_id,
                "actor_id": actor_id,
                "action": action,
                "input_hash": input_hash,
                "payload": payload,
                "status": "pending",
                "expires_at": time.time() + ttl_seconds,
                "created_at": time.time(),
            }
            self._rows[approval_id] = row
            return dict(row)

    def decide(
        self,
        approval_id: str,
        *,
        project_key: str,
        approved: bool,
        actor_id: str,
        input_hash: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            row = self._rows.get(approval_id)
            if not row or row["project"] != project_key:
                raise KeyError(approval_id)
            if time.time() > row["expires_at"]:
                row["status"] = "expired"
                raise ValueError("approval_expired")
            if input_hash and input_hash != row["input_hash"]:
                raise ValueError("material_change_invalidates_approval")
            row["status"] = "approved" if approved else "rejected"
            row["decided_by"] = actor_id
            row["decided_at"] = time.time()
            return dict(row)


class WebhookDelivery:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._log: list[dict[str, Any]] = []
        self._disabled: set[str] = set()

    def reset_for_tests(self) -> None:
        with self._lock:
            self._log.clear()
            self._disabled.clear()

    def deliver(
        self,
        *,
        project_key: str,
        url: str,
        body: dict[str, Any],
        max_attempts: int = 5,
    ) -> dict[str, Any]:
        if get_project_registry().is_killed(project_key, switch="callbacks"):
            return {"status": "killed"}
        if url in self._disabled:
            return {"status": "disabled"}
        parsed_ok = url.startswith("https://") or (
            url.startswith("http://") and ("localhost" in url or "127.0.0.1" in url)
        )
        if not parsed_ok:
            raise ValueError("callback must be allowlisted https (or local http)")
        secret = os.environ.get("KEPRIX_SIDECAR_WEBHOOK_SECRET", "dev-webhook-secret")
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
        sig = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
        entry = {
            "project": project_key,
            "url": url,
            "signature": sig,
            "attempts": 1,
            "max_attempts": max_attempts,
            "status": "queued",
            "body_digest": hashlib.sha256(raw.encode()).hexdigest(),
            "created_at": time.time(),
        }
        # Local/dev: do not perform real HTTP by default unless KEPRIX_SIDECAR_DELIVER=1
        if os.environ.get("KEPRIX_SIDECAR_DELIVER") == "1":
            import httpx

            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, content=raw, headers={"X-Keprix-Signature": sig, "Content-Type": "application/json"})
                    entry["status"] = "delivered" if resp.status_code < 300 else "failed"
                    if resp.status_code == 410:
                        self._disabled.add(url)
                        entry["status"] = "gone_disabled"
            except Exception as exc:
                entry["status"] = "failed"
                entry["error"] = str(exc)
        else:
            entry["status"] = "recorded"
        with self._lock:
            self._log.append(entry)
        return dict(entry)


_EVENT: EventService | None = None
_JOB: JobService | None = None
_APPROVAL: ApprovalStore | None = None
_WEBHOOK: WebhookDelivery | None = None
_LOCK = threading.Lock()


def get_event_service() -> EventService:
    global _EVENT
    with _LOCK:
        if _EVENT is None:
            _EVENT = EventService()
        return _EVENT


def get_job_service() -> JobService:
    global _JOB
    with _LOCK:
        if _JOB is None:
            _JOB = JobService()
        return _JOB


def get_approval_store() -> ApprovalStore:
    global _APPROVAL
    with _LOCK:
        if _APPROVAL is None:
            _APPROVAL = ApprovalStore()
        return _APPROVAL


def get_webhook_delivery() -> WebhookDelivery:
    global _WEBHOOK
    with _LOCK:
        if _WEBHOOK is None:
            _WEBHOOK = WebhookDelivery()
        return _WEBHOOK


# Back-compat alias used by nodes.py
# jobs module path historically referenced get_approval_store from jobs
