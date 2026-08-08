"""Context, memory, files, privacy, retention (KUS-07)."""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
from typing import Any

from keprix.universal_sidecar.registry import get_project_registry


class MemoryService:
    """Namespaced memory with ephemeral default and cross-tenant isolation."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rows: dict[str, dict[str, Any]] = {}
        self._deletion_receipts: list[dict[str, Any]] = []

    def reset_for_tests(self) -> None:
        with self._lock:
            self._rows.clear()
            self._deletion_receipts.clear()

    def _ns_key(
        self,
        *,
        project_key: str,
        deployment: str,
        environment: str,
        tenant_id: str,
        namespace: str,
        entry_id: str,
    ) -> str:
        return f"{project_key}|{deployment}|{environment}|{tenant_id}|{namespace}|{entry_id}"

    def write(
        self,
        *,
        project_key: str,
        tenant_id: str,
        namespace: str,
        content: str,
        source: str,
        source_version: str = "1",
        observed_class: str = "observed",
        confidence: float = 1.0,
        purpose: str = "context",
        ttl_seconds: int = 3600,
        deployment: str = "local",
        environment: str = "local",
        actor_id: str = "",
        pack: str = "universal",
    ) -> dict[str, Any]:
        if get_project_registry().is_killed(project_key, switch="memory_writes"):
            raise PermissionError("memory_writes_killed")
        row = get_project_registry().require(project_key)
        mode = (row["manifest"].get("memory") or {}).get("mode", "ephemeral")
        if mode == "disabled":
            raise PermissionError("memory_disabled")
        if mode == "ephemeral":
            namespace = "ephemeral"
            ttl_seconds = min(ttl_seconds, 3600)
        # Generated inference never auto-promoted
        verified = observed_class == "observed" and confidence >= 0.99
        entry_id = f"mem_{uuid.uuid4().hex[:12]}"
        key = self._ns_key(
            project_key=project_key,
            deployment=deployment,
            environment=environment,
            tenant_id=tenant_id or "_",
            namespace=namespace,
            entry_id=entry_id,
        )
        record = {
            "id": entry_id,
            "key": key,
            "project": project_key,
            "deployment": deployment,
            "environment": environment,
            "tenant_id": tenant_id or "_",
            "actor_id": actor_id,
            "pack": pack,
            "namespace": namespace,
            "content": content[:8000],
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            "source": source,
            "source_version": source_version,
            "class": observed_class,
            "verified": verified,
            "confidence": confidence,
            "purpose": purpose,
            "expiry": time.time() + ttl_seconds,
            "retention_class": mode,
            "created_at": time.time(),
        }
        with self._lock:
            self._rows[key] = record
        return {k: v for k, v in record.items() if k != "content"} | {"content_preview": content[:80]}

    def search(
        self,
        *,
        project_key: str,
        tenant_id: str,
        query: str,
        namespace: str = "ephemeral",
        deployment: str = "local",
        environment: str = "local",
    ) -> list[dict[str, Any]]:
        q = query.lower().strip()
        now = time.time()
        hits = []
        with self._lock:
            for row in self._rows.values():
                if row["expiry"] < now:
                    continue
                if row["project"] != project_key:
                    continue
                if row["tenant_id"] != (tenant_id or "_"):
                    continue
                if row["deployment"] != deployment or row["environment"] != environment:
                    continue
                if namespace and row["namespace"] != namespace:
                    continue
                if q and q not in row["content"].lower():
                    continue
                hits.append(
                    {
                        "id": row["id"],
                        "namespace": row["namespace"],
                        "content": row["content"],
                        "source": row["source"],
                        "verified": row["verified"],
                        "citation": f"{row['source']}@{row['source_version']}",
                    }
                )
        return hits[:20]

    def delete_scope(
        self,
        *,
        project_key: str,
        tenant_id: str = "",
        namespace: str | None = None,
    ) -> dict[str, Any]:
        removed = 0
        with self._lock:
            keys = []
            for key, row in self._rows.items():
                if row["project"] != project_key:
                    continue
                if tenant_id and row["tenant_id"] != tenant_id:
                    continue
                if namespace and row["namespace"] != namespace:
                    continue
                keys.append(key)
            for key in keys:
                del self._rows[key]
                removed += 1
            receipt = {
                "project": project_key,
                "tenant_id": tenant_id,
                "namespace": namespace,
                "removed": removed,
                "completed_at": time.time(),
                "receipt_id": f"del_{uuid.uuid4().hex[:10]}",
            }
            self._deletion_receipts.append(receipt)
        return receipt

    def expire_ephemeral(self) -> int:
        now = time.time()
        removed = 0
        with self._lock:
            keys = [k for k, r in self._rows.items() if r["expiry"] < now or r["namespace"] == "ephemeral" and r["expiry"] < now]
            for k in keys:
                if self._rows[k]["expiry"] < now:
                    del self._rows[k]
                    removed += 1
        return removed

    def dsar_export(self, *, project_key: str, tenant_id: str) -> dict[str, Any]:
        with self._lock:
            rows = [
                {k: v for k, v in r.items() if k not in {"key"}}
                for r in self._rows.values()
                if r["project"] == project_key and r["tenant_id"] == (tenant_id or "_")
            ]
        return {
            "project": project_key,
            "tenant_id": tenant_id,
            "entries": rows,
            "excludes": ["other_projects", "internal_secrets"],
        }


class FileIngest:
    """Bounded file ingestion: no macro/formula execution."""

    MAX_BYTES = 5_000_000
    MAX_FILES = 10
    ALLOWED_TYPES = frozenset(
        {
            "text/plain",
            "application/json",
            "text/markdown",
            "text/csv",
            "application/pdf",
        }
    )

    def ingest(
        self,
        *,
        project_key: str,
        content_type: str,
        data: bytes,
        filename: str = "upload",
    ) -> dict[str, Any]:
        if content_type not in self.ALLOWED_TYPES:
            raise ValueError("content_type_not_allowed")
        if len(data) > self.MAX_BYTES:
            raise ValueError("file_too_large")
        # Archive bomb / decompression: reject nested zip markers for non-pdf
        if data[:2] == b"PK" and content_type != "application/pdf":
            raise ValueError("archive_not_allowed")
        # Treat content as untrusted data, never instructions
        digest = hashlib.sha256(data).hexdigest()
        return {
            "project": project_key,
            "filename": filename[:128],
            "content_type": content_type,
            "bytes": len(data),
            "content_hash": digest,
            "sandbox_conversion": "none",
            "macros_executed": False,
            "instruction_separated": True,
        }


_MEMORY: MemoryService | None = None
_LOCK = threading.Lock()


def get_memory_service() -> MemoryService:
    global _MEMORY
    with _LOCK:
        if _MEMORY is None:
            _MEMORY = MemoryService()
        return _MEMORY
