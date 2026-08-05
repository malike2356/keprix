"""EgressAudit: NDJSON log of outbound HTTP decisions (ALLOWED and BLOCKED).

Writes to logs/egress/YYYY-MM-DD.ndjson. Each entry records the product,
destination host, resolved IP, decision, reason, and tool context.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LOG_DIR = Path("logs") / "egress"


@dataclass
class EgressAuditEntry:
    product_id: str
    host: str
    ip: str
    url_path: str
    decision: str          # "ALLOWED" | "BLOCKED"
    reason: str
    session_id: str | None
    tool_name: str | None
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.timestamp,
            "product_id": self.product_id,
            "host": self.host,
            "ip": self.ip,
            "url_path": self.url_path,
            "decision": self.decision,
            "reason": self.reason,
            "session_id": self.session_id,
            "tool_name": self.tool_name,
        }


class EgressAuditLog:
    """Write egress decisions to a daily NDJSON file.

    Usage::

        audit = EgressAuditLog()
        await audit.log_block("aiva", "192.168.1.1", "192.168.1.1",
                               "/api/internal", "private_ip_blocked")
    """

    def __init__(self, log_dir: Path | str = _LOG_DIR) -> None:
        self._log_dir = Path(log_dir)
        self._lock = asyncio.Lock()
        self._current_date: str = ""
        self._handle: Any = None

    def _day_key(self) -> str:
        return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    def _log_path(self, day: str) -> Path:
        return self._log_dir / f"{day}.ndjson"

    async def _get_handle(self):
        day = self._day_key()
        if day != self._current_date or self._handle is None:
            if self._handle is not None:
                try:
                    self._handle.close()
                except Exception:
                    pass
            self._log_dir.mkdir(parents=True, exist_ok=True)
            self._handle = open(self._log_path(day), "a", encoding="utf-8")
            self._current_date = day
        return self._handle

    async def _record(
        self,
        product_id: str,
        host: str,
        ip: str,
        url_path: str,
        decision: str,
        reason: str,
        session_id: str | None = None,
        tool_name: str | None = None,
    ) -> None:
        entry = EgressAuditEntry(
            product_id=product_id,
            host=host,
            ip=ip,
            url_path=url_path,
            decision=decision,
            reason=reason,
            session_id=session_id,
            tool_name=tool_name,
            timestamp=time.time(),
        )
        async with self._lock:
            try:
                fh = await self._get_handle()
                fh.write(json.dumps(entry.to_dict()) + "\n")
                fh.flush()
            except Exception as exc:
                logger.warning("EgressAuditLog write failed: %s", exc)

    async def log_allow(
        self,
        product_id: str,
        host: str,
        ip: str,
        url: str,
        reason: str = "host_in_allowlist",
        session_id: str | None = None,
        tool_name: str | None = None,
    ) -> None:
        await self._record(product_id, host, ip, url, "ALLOWED", reason, session_id, tool_name)

    async def log_block(
        self,
        product_id: str,
        host: str,
        ip: str,
        url: str,
        reason: str,
        session_id: str | None = None,
        tool_name: str | None = None,
    ) -> None:
        await self._record(product_id, host, ip, url, "BLOCKED", reason, session_id, tool_name)

    def tail(self, n: int = 50) -> list[dict[str, Any]]:
        path = self._log_path(self._day_key())
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        entries = []
        for line in lines[-n:]:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    def close(self) -> None:
        if self._handle is not None:
            try:
                self._handle.close()
            except Exception:
                pass
            self._handle = None


_default_audit: EgressAuditLog | None = None


def get_egress_audit() -> EgressAuditLog:
    global _default_audit
    if _default_audit is None:
        _default_audit = EgressAuditLog()
    return _default_audit


def reset_egress_audit() -> None:
    global _default_audit
    _default_audit = None
