"""ToolACLAuditLog: NDJSON log of every ACL decision (allow and deny).

Writes one JSON line per decision to a daily rotating file:
  logs/tool_acl/YYYY-MM-DD.ndjson

Every decision is recorded regardless of outcome so operators can audit
both allowed calls and denial patterns.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .tool_acl import ACLDecision

logger = logging.getLogger(__name__)

_LOG_DIR = Path("logs") / "tool_acl"


@dataclass
class ACLAuditEntry:
    product_id: str
    tool_name: str
    decision: ACLDecision
    workspace_id: str | None
    session_id: str | None
    timestamp: float
    action: str | None = None
    service: str | None = None
    resource_kind: str | None = None
    resource_id: str | None = None
    actor_type: str | None = None
    actor_id: str | None = None
    reason: str | None = None
    policy_decision: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ts": self.timestamp,
            "product_id": self.product_id,
            "tool_name": self.tool_name,
            "decision": self.decision.value,
            "workspace_id": self.workspace_id,
            "session_id": self.session_id,
        }
        if self.action:
            payload["action"] = self.action
        if self.service:
            payload["service"] = self.service
        if self.resource_kind:
            payload["resource_kind"] = self.resource_kind
        if self.resource_id:
            payload["resource_id"] = self.resource_id
        if self.actor_type:
            payload["actor_type"] = self.actor_type
        if self.actor_id:
            payload["actor_id"] = self.actor_id
        if self.reason:
            payload["reason"] = self.reason
        if self.policy_decision:
            payload["policy_decision"] = self.policy_decision
        return payload


class ToolACLAuditLog:
    """Writes ACL decisions to a daily NDJSON file.

    Usage::

        log = ToolACLAuditLog()
        await log.record("aiva", "terminal:run", ACLDecision.DENIED, workspace_id="ws-1")
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

    async def record(
        self,
        product_id: str,
        tool_name: str,
        decision: ACLDecision,
        workspace_id: str | None = None,
        session_id: str | None = None,
        *,
        action: str | None = None,
        service: str | None = None,
        resource_kind: str | None = None,
        resource_id: str | None = None,
        actor_type: str | None = None,
        actor_id: str | None = None,
        reason: str | None = None,
        policy_decision: dict[str, Any] | None = None,
    ) -> None:
        entry = ACLAuditEntry(
            product_id=product_id,
            tool_name=tool_name,
            decision=decision,
            workspace_id=workspace_id,
            session_id=session_id,
            timestamp=time.time(),
            action=action,
            service=service,
            resource_kind=resource_kind,
            resource_id=resource_id,
            actor_type=actor_type,
            actor_id=actor_id,
            reason=reason,
            policy_decision=policy_decision,
        )
        async with self._lock:
            try:
                fh = await self._get_handle()
                fh.write(json.dumps(entry.to_dict()) + "\n")
                fh.flush()
            except Exception as exc:
                logger.warning("ToolACLAuditLog write failed: %s", exc)
        if decision != ACLDecision.ALLOWED:
            try:
                from keprix.security.scout_integration import emit_tool_acl_signal

                emit_tool_acl_signal(
                    product_id=product_id,
                    tool_name=tool_name,
                    decision=decision.value,
                    workspace_id=workspace_id,
                )
            except Exception:
                pass

    def tail(self, n: int = 50) -> list[dict[str, Any]]:
        """Return the last n entries from today's log file (synchronous)."""
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


_default_audit: ToolACLAuditLog | None = None


def get_acl_audit_log() -> ToolACLAuditLog:
    global _default_audit
    if _default_audit is None:
        _default_audit = ToolACLAuditLog()
    return _default_audit


def reset_acl_audit_log() -> None:
    global _default_audit
    _default_audit = None
