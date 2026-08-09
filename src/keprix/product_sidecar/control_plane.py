"""Approvals, idempotency, receipts, and projection drift (prompt 641).

Owns Soft Wall lifecycle, tenant-scoped idempotency fingerprints, redacted
execution receipts, and report-only drift detection. Propreneur remains the
record source of truth; Keprix stores control-plane evidence and projections.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from typing import Any

from keprix.product_sidecar.persistence import DurableJsonStore


class IdempotencyConflict(Exception):
    def __init__(self, message: str, *, current: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.current = current or {}


class ApprovalStore:
    """Durable Soft Wall approvals (one bus for pack invoke and chat resume)."""

    def __init__(self, *, durable: bool = True) -> None:
        self._lock = threading.RLock()
        self._items: dict[str, dict[str, Any]] = {}
        self._durable = DurableJsonStore("approvals") if durable else None
        if self._durable:
            for row in self._durable.items():
                approval_id = str(row.get("approval_id") or "")
                if approval_id:
                    self._items[approval_id] = row

    def reset_for_tests(self) -> None:
        with self._lock:
            self._items.clear()
            if self._durable:
                self._durable.reset_for_tests()

    def _persist(self, row: dict[str, Any]) -> None:
        if self._durable:
            self._durable.put(str(row["approval_id"]), row)

    def _expire_if_needed(self, row: dict[str, Any]) -> dict[str, Any]:
        if row.get("status") == "pending" and time.time() > float(row.get("expires_at") or 0):
            row["status"] = "expired"
            row["expired_at"] = time.time()
            self._persist(row)
        return row

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
        actor_id: str = "",
        operation_id: str = "",
        correlation_id: str = "",
        conversation_id: str = "",
    ) -> dict[str, Any]:
        """Create or reuse a pending approval for the same input fingerprint."""
        with self._lock:
            for row in self._items.values():
                self._expire_if_needed(row)
                if (
                    row.get("product") == product
                    and row.get("workspace_id") == workspace_id
                    and row.get("node_key") == node_key
                    and row.get("input_hash") == input_hash
                    and row.get("status") == "pending"
                ):
                    # One Soft Wall for one action (no duplicate pending approvals).
                    return dict(row)

            approval_id = f"appr_{uuid.uuid4().hex[:12]}"
            row = {
                "approval_id": approval_id,
                "product": product,
                "workspace_id": workspace_id,
                "node_key": node_key,
                "operation_id": operation_id or node_key,
                "input_hash": input_hash,
                "reason": reason,
                "deep_link": deep_link or f"/propreneur/soft-wall?approval_id={approval_id}&kind={node_key}",
                "status": "pending",
                "created_at": time.time(),
                "expires_at": time.time() + ttl_seconds,
                "decision": None,
                "actor_id": actor_id,
                "correlation_id": correlation_id,
                "conversation_id": conversation_id,
                "execution_receipt_id": None,
                "revoked_at": None,
            }
            self._items[approval_id] = row
            self._persist(row)
            return dict(row)

    def get(self, approval_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._items.get(approval_id)
            if not row:
                return None
            return dict(self._expire_if_needed(row))

    def count_pending(self, *, product: str | None = None) -> int:
        with self._lock:
            n = 0
            for row in self._items.values():
                self._expire_if_needed(row)
                if row.get("status") != "pending":
                    continue
                if product and row.get("product") != product:
                    continue
                n += 1
            return n

    def list_pending(self, *, product: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows: list[dict[str, Any]] = []
            for row in self._items.values():
                self._expire_if_needed(row)
                if row.get("status") != "pending":
                    continue
                if product and row.get("product") != product:
                    continue
                rows.append(dict(row))
            rows.sort(key=lambda r: float(r.get("created_at") or 0), reverse=True)
            return rows[:limit]

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
            self._expire_if_needed(row)
            if row["status"] == "expired":
                raise ValueError("approval_expired")
            if row["status"] == "revoked":
                raise ValueError("approval_revoked")
            if input_hash and input_hash != row["input_hash"]:
                raise ValueError("approval_stale_hash")
            if row["status"] == "approved" and approved:
                return dict(row)
            if row["status"] == "rejected" and not approved:
                return dict(row)
            if row["status"] in {"approved", "rejected"} and bool(row["status"] == "approved") != approved:
                raise ValueError("approval_decision_conflict")
            row["status"] = "approved" if approved else "rejected"
            row["decision"] = {"actor_id": actor_id, "at": time.time(), "approved": approved}
            self._persist(row)
            return dict(row)

    def revoke(self, approval_id: str, *, workspace_id: str, actor_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._items.get(approval_id)
            if not row or row["workspace_id"] != workspace_id:
                raise KeyError("approval_not_found")
            self._expire_if_needed(row)
            if row["status"] == "revoked":
                return dict(row)
            if row["status"] not in {"pending", "approved"}:
                raise ValueError(f"approval_not_revokable:{row['status']}")
            row["status"] = "revoked"
            row["revoked_at"] = time.time()
            row["decision"] = {
                "actor_id": actor_id,
                "at": time.time(),
                "approved": False,
                "revoked": True,
            }
            self._persist(row)
            return dict(row)

    def expire(self, approval_id: str, *, workspace_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._items.get(approval_id)
            if not row or row["workspace_id"] != workspace_id:
                raise KeyError("approval_not_found")
            if row["status"] == "expired":
                return dict(row)
            if row["status"] != "pending":
                raise ValueError(f"approval_not_expirable:{row['status']}")
            row["status"] = "expired"
            row["expires_at"] = time.time()
            row["expired_at"] = time.time()
            self._persist(row)
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

    def attach_receipt(self, approval_id: str, receipt_id: str) -> None:
        with self._lock:
            row = self._items.get(approval_id)
            if not row:
                return
            row["execution_receipt_id"] = receipt_id
            self._persist(row)


class IdempotencyLedger:
    """Tenant-scoped durable idempotency with fingerprint mismatch rejection."""

    def __init__(self, *, durable: bool = True) -> None:
        self._lock = threading.RLock()
        self._items: dict[str, dict[str, Any]] = {}
        self._durable = DurableJsonStore("idempotency") if durable else None
        if self._durable:
            for row in self._durable.items():
                key = str(row.get("ledger_key") or "")
                if key:
                    self._items[key] = row

    def reset_for_tests(self) -> None:
        with self._lock:
            self._items.clear()
            if self._durable:
                self._durable.reset_for_tests()

    @staticmethod
    def _ledger_key(product: str, workspace_id: str, idempotency_key: str) -> str:
        return f"{product}:{workspace_id}:{idempotency_key}"

    def _persist(self, row: dict[str, Any]) -> None:
        if self._durable:
            self._durable.put(str(row["ledger_key"]), row)

    def begin(
        self,
        *,
        product: str,
        workspace_id: str,
        actor_id: str,
        operation: str,
        idempotency_key: str,
        input_hash: str,
    ) -> dict[str, Any]:
        if not idempotency_key:
            return {"state": "bypass"}
        key = self._ledger_key(product, workspace_id, idempotency_key)
        with self._lock:
            existing = self._items.get(key)
            if existing:
                fingerprint = {
                    "operation": existing.get("operation"),
                    "actor_id": existing.get("actor_id"),
                    "workspace_id": existing.get("workspace_id"),
                    "input_hash": existing.get("input_hash"),
                }
                incoming = {
                    "operation": operation,
                    "actor_id": actor_id,
                    "workspace_id": workspace_id,
                    "input_hash": input_hash,
                }
                if fingerprint != incoming:
                    raise IdempotencyConflict(
                        "idempotency_fingerprint_mismatch",
                        current={
                            "idempotency_key": idempotency_key,
                            "stored": fingerprint,
                            "requested": incoming,
                            "result": existing.get("result"),
                            "retry": {
                                "safe": False,
                                "guidance": "Use a new Idempotency-Key for a different operation, actor, workspace, or payload.",
                            },
                        },
                    )
                if existing.get("state") == "completed":
                    return {
                        "state": "replay",
                        "result": dict(existing.get("result") or {}),
                        "ledger_key": key,
                    }
                return {"state": "inflight", "ledger_key": key}

            row = {
                "ledger_key": key,
                "product": product,
                "workspace_id": workspace_id,
                "actor_id": actor_id,
                "operation": operation,
                "idempotency_key": idempotency_key,
                "input_hash": input_hash,
                "state": "inflight",
                "result": None,
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            self._items[key] = row
            self._persist(row)
            return {"state": "fresh", "ledger_key": key}

    def complete(self, ledger_key: str, result: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            row = self._items.get(ledger_key)
            if not row:
                return result
            row["state"] = "completed"
            row["result"] = dict(result)
            row["updated_at"] = time.time()
            self._persist(row)
            return dict(result)


class ExecutionReceiptStore:
    """Redacted receipts linking turn → approval → domain result."""

    SENSITIVE_KEYS = frozenset(
        {
            "password",
            "token",
            "secret",
            "api_key",
            "authorization",
            "ssn",
            "card_number",
            "notes",
            "body",
            "content",
            "email",
            "phone",
        }
    )

    def __init__(self, *, durable: bool = True) -> None:
        self._lock = threading.RLock()
        self._items: dict[str, dict[str, Any]] = {}
        self._durable = DurableJsonStore("execution_receipts") if durable else None
        if self._durable:
            for row in self._durable.items():
                rid = str(row.get("receipt_id") or "")
                if rid:
                    self._items[rid] = row

    def reset_for_tests(self) -> None:
        with self._lock:
            self._items.clear()
            if self._durable:
                self._durable.reset_for_tests()

    def _redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for k, v in value.items():
                if str(k).lower() in self.SENSITIVE_KEYS or "secret" in str(k).lower():
                    out[k] = "[redacted]"
                else:
                    out[k] = self._redact(v)
            return out
        if isinstance(value, list):
            return [self._redact(v) for v in value[:20]]
        if isinstance(value, str) and len(value) > 240:
            return value[:240] + "…"
        return value

    def record(
        self,
        *,
        product: str,
        workspace_id: str,
        node_key: str,
        status: str,
        correlation_id: str = "",
        conversation_id: str = "",
        tool_call_id: str = "",
        approval_id: str = "",
        record_id: str = "",
        audit_event_id: str = "",
        method: str = "",
        path: str = "",
        result_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        receipt_id = f"rcpt_{uuid.uuid4().hex[:14]}"
        row = {
            "receipt_id": receipt_id,
            "product": product,
            "workspace_id": workspace_id,
            "node_key": node_key,
            "status": status,
            "correlation_id": correlation_id,
            "conversation_id": conversation_id,
            "tool_call_id": tool_call_id,
            "approval_id": approval_id,
            "record_id": record_id,
            "audit_event_id": audit_event_id,
            "method": method,
            "path": path,
            "result_summary": self._redact(result_summary or {}),
            "created_at": time.time(),
        }
        with self._lock:
            self._items[receipt_id] = row
            if self._durable:
                self._durable.put(receipt_id, row)
            return dict(row)

    def get(self, receipt_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._items.get(receipt_id)
            return dict(row) if row else None

    def list_for_workspace(self, workspace_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = [dict(r) for r in self._items.values() if r.get("workspace_id") == workspace_id]
            rows.sort(key=lambda r: float(r.get("created_at") or 0), reverse=True)
            return rows[:limit]

    def list_for_product(self, product: str, *, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = [dict(r) for r in self._items.values() if r.get("product") == product]
            rows.sort(key=lambda r: float(r.get("created_at") or 0), reverse=True)
            return rows[:limit]


def fingerprint_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def detect_projection_drift(
    *,
    product: str,
    workspace_id: str,
    contract_records: list[dict[str, Any]],
    projected_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare contract-visible ids/versions; report repair actions only (no overwrite)."""
    contract_map = {
        str(r.get("id") or r.get("record_id") or ""): r for r in contract_records if r.get("id") or r.get("record_id")
    }
    projected_map = {
        str(r.get("id") or r.get("record_id") or ""): r
        for r in projected_records
        if r.get("id") or r.get("record_id")
    }
    missing_in_projection: list[str] = []
    version_mismatch: list[dict[str, Any]] = []
    extra_in_projection: list[str] = []
    for rid, crow in contract_map.items():
        prow = projected_map.get(rid)
        if prow is None:
            missing_in_projection.append(rid)
            continue
        cv = crow.get("version") or crow.get("etag")
        pv = prow.get("version") or prow.get("etag")
        if cv is not None and pv is not None and str(cv) != str(pv):
            version_mismatch.append(
                {
                    "record_id": rid,
                    "contract_version": cv,
                    "projected_version": pv,
                    "repair": "refresh_projection_from_propreneur",
                }
            )
    for rid in projected_map:
        if rid not in contract_map:
            extra_in_projection.append(rid)

    actions = []
    for rid in missing_in_projection:
        actions.append({"action": "pull_from_propreneur", "record_id": rid})
    for item in version_mismatch:
        actions.append({"action": "refresh_projection_from_propreneur", "record_id": item["record_id"]})
    for rid in extra_in_projection:
        actions.append(
            {
                "action": "flag_orphan_projection",
                "record_id": rid,
                "note": "Do not delete Propreneur records; investigate projection only.",
            }
        )

    return {
        "product": product,
        "workspace_id": workspace_id,
        "source_of_truth": "propreneur",
        "silent_overwrite": False,
        "missing_in_projection": missing_in_projection,
        "version_mismatch": version_mismatch,
        "extra_in_projection": extra_in_projection,
        "repair_actions": actions,
        "converged": not (missing_in_projection or version_mismatch or extra_in_projection),
    }
