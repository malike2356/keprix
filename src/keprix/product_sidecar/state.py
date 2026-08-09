"""Jobs, events, approvals, shadow, circuit, kill switches, memory traces."""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
from typing import Any

from keprix.product_sidecar.control_plane import (
    ApprovalStore,
    ExecutionReceiptStore,
    IdempotencyLedger,
)
from keprix.product_sidecar.persistence import DurableJsonStore


class JobStore:
    def __init__(self, *, durable: bool = True) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._durable = DurableJsonStore("jobs") if durable else None
        if self._durable:
            for row in self._durable.items():
                job_id = str(row.get("job_id") or "")
                if job_id:
                    self._jobs[job_id] = row

    def reset_for_tests(self) -> None:
        with self._lock:
            self._jobs.clear()
            if self._durable:
                self._durable.reset_for_tests()

    def _persist(self, row: dict[str, Any]) -> None:
        if self._durable:
            self._durable.put(str(row["job_id"]), row)

    def create(
        self,
        *,
        product: str,
        workspace_id: str,
        node_key: str,
        input_payload: dict[str, Any],
        idempotency_key: str = "",
        checkpoint: dict[str, Any] | None = None,
        budget_units: int = 1,
    ) -> dict[str, Any]:
        with self._lock:
            if idempotency_key:
                for job in self._jobs.values():
                    if (
                        job["workspace_id"] == workspace_id
                        and job.get("idempotency_key") == idempotency_key
                        and job["node_key"] == node_key
                        and job.get("product") == product
                    ):
                        return dict(job)
            job_id = f"job_{uuid.uuid4().hex[:16]}"
            row = {
                "job_id": job_id,
                "product": product,
                "workspace_id": workspace_id,
                "node_key": node_key,
                "status": "queued",
                "progress": 0,
                "input": input_payload,
                "idempotency_key": idempotency_key,
                "created_at": time.time(),
                "updated_at": time.time(),
                "result": None,
                "result_ref": None,
                "cancel_requested": False,
                "attempts": 0,
                "checkpoint": checkpoint or {},
                "budget_units": budget_units,
                "dead_letter_reason": None,
            }
            self._jobs[job_id] = row
            self._persist(row)
            return dict(row)

    def get(self, job_id: str, *, workspace_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job["workspace_id"] != workspace_id:
                return None
            return dict(job)

    def list_for_product(self, product: str) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(j) for j in self._jobs.values() if j.get("product") == product]

    def cancel(self, job_id: str, *, workspace_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job["workspace_id"] != workspace_id:
                return None
            if job["status"] in {"cancelled", "completed", "failed"}:
                return dict(job)
            job["status"] = "cancelled"
            job["cancel_requested"] = True
            job["updated_at"] = time.time()
            self._persist(job)
            return dict(job)

    def mark_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job["status"] == "queued":
                job["status"] = "running"
                job["progress"] = 10
                job["attempts"] = int(job.get("attempts") or 0) + 1
                job["updated_at"] = time.time()
                self._persist(job)

    def checkpoint(self, job_id: str, checkpoint: dict[str, Any], *, progress: int | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job["checkpoint"] = dict(checkpoint)
            if progress is not None:
                job["progress"] = progress
            job["updated_at"] = time.time()
            self._persist(job)

    def complete(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            if job["status"] == "cancelled":
                return
            job["status"] = "completed"
            job["progress"] = 100
            job["result"] = result
            job["result_ref"] = f"job://{job_id}/result"
            job["updated_at"] = time.time()
            self._persist(job)

    def dead_letter(self, job_id: str, reason: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job["status"] = "failed"
            job["dead_letter_reason"] = reason
            job["updated_at"] = time.time()
            self._persist(job)


class EventStore:
    def __init__(self, *, durable: bool = True) -> None:
        self._lock = threading.RLock()
        self._seen: set[tuple[str, str, str]] = set()  # product, deployment, event_id
        self._events: list[dict[str, Any]] = []
        self._cursor = 0
        self._durable = DurableJsonStore("events") if durable else None
        if self._durable:
            for row in self._durable.items():
                self._events.append(row)
                product = str(row.get("source") or row.get("product") or "")
                deployment = str(row.get("deployment") or "local")
                event_id = str(row.get("id") or "")
                if event_id:
                    self._seen.add((product, deployment, event_id))
            self._cursor = int(self._durable.get_meta("cursor") or len(self._events))

    def reset_for_tests(self) -> None:
        with self._lock:
            self._seen.clear()
            self._events.clear()
            self._cursor = 0
            if self._durable:
                self._durable.reset_for_tests()

    def ingest(self, envelope: dict[str, Any]) -> dict[str, Any]:
        product = str(envelope.get("source") or envelope.get("product") or "")
        deployment = str(envelope.get("deployment") or "local")
        event_id = str(envelope.get("id") or "")
        if not event_id:
            raise ValueError("event id required")
        # Echo suppression: skip Propreneur events caused by a Keprix mutation.
        causation = str(envelope.get("causation_id") or envelope.get("caused_by") or "")
        if causation.startswith("keprix:") or envelope.get("echo_of_keprix_mutation"):
            return {
                "accepted": True,
                "deduped": True,
                "echo_suppressed": True,
                "id": event_id,
                "causation_id": causation,
            }
        key = (product, deployment, event_id)
        with self._lock:
            if key in self._seen:
                return {"accepted": True, "deduped": True, "id": event_id}
            self._seen.add(key)
            row = dict(envelope)
            row.setdefault("seq", self._cursor + 1)
            row.setdefault("ingested_at", time.time())
            row.setdefault("acked", False)
            self._events.append(row)
            self._cursor += 1
            if self._durable:
                self._durable.put(event_id, row)
                self._durable.set_meta("cursor", self._cursor)
            return {"accepted": True, "deduped": False, "id": event_id, "seq": row["seq"]}

    def ack(self, event_id: str, *, product: str = "") -> dict[str, Any]:
        with self._lock:
            for event in self._events:
                if str(event.get("id") or "") != event_id:
                    continue
                if product and event.get("product") != product and event.get("source") != product:
                    continue
                event["acked"] = True
                event["acked_at"] = time.time()
                if self._durable:
                    self._durable.put(event_id, event)
                return {"acked": True, "id": event_id, "seq": event.get("seq")}
            return {"acked": False, "id": event_id, "error": "not_found"}

    def list_for_product(self, product: str) -> list[dict[str, Any]]:
        with self._lock:
            return [
                dict(e)
                for e in self._events
                if e.get("product") == product or e.get("source") == product
            ]

    def stream_since(self, product: str, *, cursor: int = 0, limit: int = 100) -> dict[str, Any]:
        with self._lock:
            rows = []
            for event in self._events:
                seq = int(event.get("seq") or 0)
                if seq <= cursor:
                    continue
                if event.get("product") != product and event.get("source") != product:
                    continue
                rows.append(dict(event))
                if len(rows) >= limit:
                    break
            next_cursor = rows[-1]["seq"] if rows else cursor
            return {"events": rows, "cursor": next_cursor, "product": product}


class ShadowStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rows: list[dict[str, Any]] = []

    def reset_for_tests(self) -> None:
        with self._lock:
            self._rows.clear()

    def record(self, comparison: dict[str, Any]) -> dict[str, Any]:
        row = dict(comparison)
        row.setdefault("id", f"shadow_{uuid.uuid4().hex[:10]}")
        row.setdefault("at", time.time())
        with self._lock:
            self._rows.append(row)
            if len(self._rows) > 2000:
                self._rows = self._rows[-1000:]
            return dict(row)

    def list_for_workspace(self, workspace_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = [r for r in self._rows if r.get("workspace_id") == workspace_id]
            return list(reversed(rows[-limit:]))


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 5, cool_down_seconds: float = 30.0) -> None:
        self._lock = threading.RLock()
        self._failures = 0
        self._opened_at: float | None = None
        self._threshold = failure_threshold
        self._cool_down = cool_down_seconds
        self._idempotency: dict[str, dict[str, Any]] = {}

    def reset_for_tests(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None
            self._idempotency.clear()

    def allow(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if time.time() - self._opened_at >= self._cool_down:
                self._opened_at = None
                self._failures = 0
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self._threshold:
                self._opened_at = time.time()

    def state(self) -> str:
        return "closed" if self.allow() else "open"

    def remember_side_effect(self, idempotency_key: str, result: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if idempotency_key in self._idempotency:
                return dict(self._idempotency[idempotency_key])
            self._idempotency[idempotency_key] = dict(result)
            return dict(result)

    def get_side_effect(self, idempotency_key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._idempotency.get(idempotency_key)
            return dict(row) if row else None


class KillSwitchBoard:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.force_carina = False
        self.outbound_kill = False
        self.provider_disabled: set[str] = set()
        self.shadow_enabled_global = True
        self.shadow_workspaces: set[str] = set()
        self.primary_workspaces: set[str] = set()
        self.budgets: dict[tuple[str, str], int] = {}  # workspace, node -> remaining

    def reset_for_tests(self) -> None:
        with self._lock:
            self.force_carina = False
            self.outbound_kill = False
            self.provider_disabled.clear()
            self.shadow_enabled_global = True
            self.shadow_workspaces.clear()
            self.primary_workspaces.clear()
            self.budgets.clear()

    def set_budget(self, workspace_id: str, node_key: str, units: int) -> None:
        with self._lock:
            self.budgets[(workspace_id, node_key)] = units

    def consume_budget(self, workspace_id: str, node_key: str, units: int) -> bool:
        with self._lock:
            key = (workspace_id, node_key)
            if key not in self.budgets:
                return True
            if self.budgets[key] < units:
                return False
            self.budgets[key] -= units
            return True


class EphemeralMemory:
    """Wave-1 shadow: ephemeral only. Wave-2 primary: durable namespaced store."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._durable: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._ephemeral: dict[tuple[str, str, str], dict[str, Any]] = {}

    def reset_for_tests(self) -> None:
        with self._lock:
            self._durable.clear()
            self._ephemeral.clear()

    def put(
        self,
        *,
        product: str,
        workspace_id: str,
        key: str,
        value: dict[str, Any],
        durable: bool,
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = {
            "key": key,
            "value": value,
            "provenance": provenance or {},
            "updated_at": time.time(),
        }
        slot = (product, workspace_id, key)
        with self._lock:
            store = self._durable if durable else self._ephemeral
            store[slot] = row
            return dict(row)

    def get(self, *, product: str, workspace_id: str, key: str) -> dict[str, Any] | None:
        slot = (product, workspace_id, key)
        with self._lock:
            row = self._durable.get(slot) or self._ephemeral.get(slot)
            return dict(row) if row else None

    def delete_workspace(self, *, product: str, workspace_id: str) -> int:
        with self._lock:
            removed = 0
            for store in (self._durable, self._ephemeral):
                keys = [k for k in store if k[0] == product and k[1] == workspace_id]
                for k in keys:
                    del store[k]
                    removed += 1
            return removed

    def delete_product(self, product: str) -> int:
        with self._lock:
            removed = 0
            for store in (self._durable, self._ephemeral):
                keys = [k for k in store if k[0] == product]
                for k in keys:
                    del store[k]
                    removed += 1
            return removed

    def get_cross_product(self, *, product: str, other_product: str, workspace_id: str, key: str) -> None:
        """Cross-product memory reads are impossible by construction."""
        if product != other_product:
            raise PermissionError("cross_product_memory")
        return None


def input_hash(payload: dict[str, Any]) -> str:
    import json

    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


_JOBS = JobStore()
_EVENTS = EventStore()
_APPROVALS = ApprovalStore(durable=True)
_IDEMPOTENCY = IdempotencyLedger(durable=True)
_RECEIPTS = ExecutionReceiptStore(durable=True)
_SHADOW = ShadowStore()
_CIRCUIT = CircuitBreaker()
_KILLS = KillSwitchBoard()
_MEMORY = EphemeralMemory()


def get_job_store() -> JobStore:
    return _JOBS


def get_event_store() -> EventStore:
    return _EVENTS


def get_approval_store() -> ApprovalStore:
    return _APPROVALS


def get_idempotency_ledger() -> IdempotencyLedger:
    return _IDEMPOTENCY


def get_receipt_store() -> ExecutionReceiptStore:
    return _RECEIPTS


def get_shadow_store() -> ShadowStore:
    return _SHADOW


def get_circuit() -> CircuitBreaker:
    return _CIRCUIT


def get_kill_switches() -> KillSwitchBoard:
    return _KILLS


def get_memory_store() -> EphemeralMemory:
    return _MEMORY


def reset_all_sidecar_state_for_tests() -> None:
    global _JOBS, _EVENTS, _APPROVALS, _IDEMPOTENCY, _RECEIPTS, _SHADOW, _CIRCUIT, _KILLS, _MEMORY
    _JOBS.reset_for_tests()
    _EVENTS.reset_for_tests()
    # Recreate durable-backed stores so KEPRIX_DATA_DIR changes take effect
    _JOBS = JobStore(durable=True)
    _EVENTS = EventStore(durable=True)
    _APPROVALS = ApprovalStore(durable=True)
    _IDEMPOTENCY = IdempotencyLedger(durable=True)
    _RECEIPTS = ExecutionReceiptStore(durable=True)
    _SHADOW = ShadowStore()
    _CIRCUIT = CircuitBreaker()
    _KILLS = KillSwitchBoard()
    _MEMORY = EphemeralMemory()
    from keprix.product_sidecar.persistence import get_provision_store

    get_provision_store().reset_for_tests()
