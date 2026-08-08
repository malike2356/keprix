"""Jobs, events, approvals, shadow, circuit, kill switches, memory traces."""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
from typing import Any


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, dict[str, Any]] = {}

    def reset_for_tests(self) -> None:
        with self._lock:
            self._jobs.clear()

    def create(
        self,
        *,
        product: str,
        workspace_id: str,
        node_key: str,
        input_payload: dict[str, Any],
        idempotency_key: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            if idempotency_key:
                for job in self._jobs.values():
                    if (
                        job["workspace_id"] == workspace_id
                        and job.get("idempotency_key") == idempotency_key
                        and job["node_key"] == node_key
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
                "cancel_requested": False,
            }
            self._jobs[job_id] = row
            return dict(row)

    def get(self, job_id: str, *, workspace_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job["workspace_id"] != workspace_id:
                return None
            return dict(job)

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
            return dict(job)

    def mark_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job["status"] == "queued":
                job["status"] = "running"
                job["progress"] = 10
                job["updated_at"] = time.time()

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
            job["updated_at"] = time.time()


class EventStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._seen: set[tuple[str, str, str]] = set()  # product, deployment, event_id
        self._events: list[dict[str, Any]] = []

    def reset_for_tests(self) -> None:
        with self._lock:
            self._seen.clear()
            self._events.clear()

    def ingest(self, envelope: dict[str, Any]) -> dict[str, Any]:
        product = str(envelope.get("source") or envelope.get("product") or "")
        deployment = str(envelope.get("deployment") or "local")
        event_id = str(envelope.get("id") or "")
        if not event_id:
            raise ValueError("event id required")
        key = (product, deployment, event_id)
        with self._lock:
            if key in self._seen:
                return {"accepted": True, "deduped": True, "id": event_id}
            self._seen.add(key)
            self._events.append(dict(envelope))
            return {"accepted": True, "deduped": False, "id": event_id}


class ApprovalStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: dict[str, dict[str, Any]] = {}

    def reset_for_tests(self) -> None:
        with self._lock:
            self._items.clear()

    def request(
        self,
        *,
        product: str,
        workspace_id: str,
        node_key: str,
        input_hash: str,
        reason: str,
        deep_link: str,
        ttl_seconds: int = 3600,
    ) -> dict[str, Any]:
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        row = {
            "approval_id": approval_id,
            "product": product,
            "workspace_id": workspace_id,
            "node_key": node_key,
            "input_hash": input_hash,
            "reason": reason,
            "deep_link": deep_link,
            "status": "pending",
            "created_at": time.time(),
            "expires_at": time.time() + ttl_seconds,
            "decision": None,
        }
        with self._lock:
            self._items[approval_id] = row
            return dict(row)

    def get(self, approval_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._items.get(approval_id)
            return dict(row) if row else None

    def decide(
        self,
        approval_id: str,
        *,
        workspace_id: str,
        approved: bool,
        actor_id: str,
        input_hash: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            row = self._items.get(approval_id)
            if not row or row["workspace_id"] != workspace_id:
                raise KeyError("approval_not_found")
            if time.time() > float(row["expires_at"]):
                row["status"] = "expired"
                raise ValueError("approval_expired")
            if input_hash and input_hash != row["input_hash"]:
                raise ValueError("approval_stale_hash")
            if row["status"] == "approved" and approved:
                return dict(row)  # idempotent
            if row["status"] == "rejected" and not approved:
                return dict(row)
            row["status"] = "approved" if approved else "rejected"
            row["decision"] = {"actor_id": actor_id, "at": time.time(), "approved": approved}
            return dict(row)

    def is_approved(self, approval_id: str, *, workspace_id: str, input_hash: str) -> bool:
        row = self.get(approval_id)
        if not row or row["workspace_id"] != workspace_id:
            return False
        if row["status"] != "approved":
            return False
        if time.time() > float(row["expires_at"]):
            return False
        return row["input_hash"] == input_hash


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


def input_hash(payload: dict[str, Any]) -> str:
    import json

    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


_JOBS = JobStore()
_EVENTS = EventStore()
_APPROVALS = ApprovalStore()
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


def get_shadow_store() -> ShadowStore:
    return _SHADOW


def get_circuit() -> CircuitBreaker:
    return _CIRCUIT


def get_kill_switches() -> KillSwitchBoard:
    return _KILLS


def get_memory_store() -> EphemeralMemory:
    return _MEMORY


def reset_all_sidecar_state_for_tests() -> None:
    _JOBS.reset_for_tests()
    _EVENTS.reset_for_tests()
    _APPROVALS.reset_for_tests()
    _SHADOW.reset_for_tests()
    _CIRCUIT.reset_for_tests()
    _KILLS.reset_for_tests()
    _MEMORY.reset_for_tests()
