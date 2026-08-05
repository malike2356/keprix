"""Provider audit trail: structured append-only log of every routing decision."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    timestamp: float
    request_id: str
    tenant_id: str
    provider: str
    model: str
    tier_id: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    success: bool
    error: str = ""
    combo_id: str = ""
    no_log: bool = False            # True = content was redacted in logging
    pii_masked: bool = False
    injection_detected: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class ProviderAuditLog:
    """Append-only audit log written as NDJSON (newline-delimited JSON).

    One file per day, rotated by wall-clock date. Safe for concurrent writes
    via an asyncio lock. Designed for offline compliance inspection rather
    than real-time querying - for production use, ship these files to your
    SIEM or object storage.

    Usage::

        audit = ProviderAuditLog(directory="/var/log/keprix/audit")
        await audit.record(AuditEntry(...))
    """

    def __init__(self, directory: str | Path = "logs/audit") -> None:
        self._dir  = Path(directory)
        self._lock = asyncio.Lock()
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for_today(self) -> Path:
        import datetime
        date_str = datetime.date.today().isoformat()
        return self._dir / f"audit-{date_str}.ndjson"

    async def record(self, entry: AuditEntry) -> None:
        """Append an audit entry to today's log file."""
        line = json.dumps(asdict(entry), separators=(",", ":")) + "\n"
        async with self._lock:
            try:
                with open(self._path_for_today(), "a", encoding="utf-8") as fh:
                    fh.write(line)
            except OSError as exc:
                logger.error("Audit write failed: %s", exc)

    async def record_routing(
        self,
        *,
        request_id: str,
        tenant_id: str,
        provider: str,
        model: str,
        tier_id: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        success: bool = True,
        error: str = "",
        combo_id: str = "",
        no_log: bool = False,
        pii_masked: bool = False,
        injection_detected: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Convenience wrapper that timestamps and records a routing event."""
        entry = AuditEntry(
            timestamp=time.time(),
            request_id=request_id,
            tenant_id=tenant_id,
            provider=provider,
            model=model,
            tier_id=tier_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            success=success,
            error=error,
            combo_id=combo_id,
            no_log=no_log,
            pii_masked=pii_masked,
            injection_detected=injection_detected,
            metadata=metadata or {},
        )
        await self.record(entry)

    async def tail(self, n: int = 50) -> list[AuditEntry]:
        """Return the last ``n`` entries from today's audit log."""
        path = self._path_for_today()
        if not path.exists():
            return []
        lines: list[str] = []
        async with self._lock:
            with open(path, encoding="utf-8") as fh:
                lines = fh.readlines()
        entries = []
        for line in lines[-n:]:
            try:
                d = json.loads(line)
                entries.append(AuditEntry(**d))
            except (json.JSONDecodeError, TypeError):
                pass
        return entries
