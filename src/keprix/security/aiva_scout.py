"""Aiva/Carina Scout governance for Keprix agent turns (K06).

Hooks SaaS Scout ``/v1/prompts/filter`` + ``/v1/events``, plus workspace-scoped
local kill switches that Scout (or channel /kill) can activate via
``POST /keprix/kill``.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

KEPRIX_SENSORS: tuple[dict[str, str], ...] = (
    {
        "id": "keprix_prompt_sensor",
        "monitors": "Prompt injection patterns, sensitive data leakage",
    },
    {
        "id": "keprix_tool_sensor",
        "monitors": "Unusual tool call patterns, tool abuse, excessive calls",
    },
    {
        "id": "keprix_token_sensor",
        "monitors": "Token usage spikes, cost anomalies",
    },
    {
        "id": "keprix_session_sensor",
        "monitors": "Session hijacking, cross-workspace access attempts",
    },
)


@dataclass
class KillStatus:
    active: bool
    scope: str = ""
    workspace_id: str | None = None
    reason: str = ""
    activated_by: str = ""
    activated_at: str | None = None


@dataclass
class FilterResult:
    blocked: bool
    verdict: str = "allowed"
    risk_score: float = 0.0
    reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class _KillRecord:
    id: str
    workspace_id: str | None
    scope: str
    reason: str
    activated_by: str
    activated_at: float
    deactivated_at: float | None = None


class AivaScoutGuard:
    """Scout filter / events / kill for Carina/Aiva agent loops."""

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        agent_id: str | None = None,
        timeout: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
        strict: bool | None = None,
    ) -> None:
        self._enabled = (
            _env_bool("SCOUT_ENABLED", False) if enabled is None else bool(enabled)
        )
        self._api_key = (
            api_key
            if api_key is not None
            else (
                os.environ.get("SCOUT_API_KEY", "").strip()
                or os.environ.get("KEPRIX_GOVERNANCE_API_KEY", "").strip()
            )
        )
        self._base_url = (
            base_url
            if base_url is not None
            else (
                os.environ.get("SCOUT_API_URL", "").strip()
                or os.environ.get("SCOUT_ENDPOINT", "").strip()
                or "https://console.labyrinthscout.com"
            )
        ).rstrip("/")
        self._agent_id = (
            agent_id
            if agent_id is not None
            else os.environ.get("KEPRIX_SCOUT_AGENT_ID", "").strip()
        )
        self._timeout = timeout
        self._transport = transport
        self._strict = (
            _env_bool("KEPRIX_SCOUT_STRICT", False) if strict is None else bool(strict)
        )
        self._lock = threading.RLock()
        self._kills: list[_KillRecord] = []
        self._cancel_events: dict[str, threading.Event] = {}
        self._events: list[dict[str, Any]] = []
        self._tool_counts: dict[str, list[float]] = {}

    @property
    def enabled(self) -> bool:
        return self._enabled and bool(self._api_key)

    def agent_id_for(self, workspace_id: str) -> str:
        if self._agent_id:
            return self._agent_id
        prefix = os.environ.get("KEPRIX_SCOUT_AGENT_ID_PREFIX", "keprix-aiva").strip() or "keprix-aiva"
        return f"{prefix}:{workspace_id}"

    # ── Kill switch ──────────────────────────────────────────────────────────

    def check_kill(self, workspace_id: str | None = None) -> KillStatus:
        """Return active kill for workspace or global agent_global scope."""
        with self._lock:
            now_active = [k for k in self._kills if k.deactivated_at is None]
            for record in reversed(now_active):
                if record.scope == "agent_global":
                    return KillStatus(
                        active=True,
                        scope=record.scope,
                        workspace_id=record.workspace_id,
                        reason=record.reason,
                        activated_by=record.activated_by,
                        activated_at=_iso(record.activated_at),
                    )
                if (
                    workspace_id
                    and record.scope == "workspace"
                    and record.workspace_id == workspace_id
                ):
                    return KillStatus(
                        active=True,
                        scope=record.scope,
                        workspace_id=record.workspace_id,
                        reason=record.reason,
                        activated_by=record.activated_by,
                        activated_at=_iso(record.activated_at),
                    )
        return KillStatus(active=False)

    def activate_kill(
        self,
        *,
        workspace_id: str | None = None,
        scope: str = "workspace",
        reason: str = "",
        activated_by: str = "scout",
    ) -> dict[str, Any]:
        scope_norm = (scope or "workspace").strip().lower()
        if scope_norm not in {"workspace", "agent_global"}:
            raise ValueError("scope must be workspace or agent_global")
        if scope_norm == "workspace" and not (workspace_id or "").strip():
            raise ValueError("workspace_id is required for workspace scope")

        record = _KillRecord(
            id=str(uuid.uuid4()),
            workspace_id=(workspace_id or "").strip() or None,
            scope=scope_norm,
            reason=reason or "Scout kill switch activated",
            activated_by=activated_by or "scout",
            activated_at=time.time(),
        )
        with self._lock:
            self._kills.append(record)
            if record.workspace_id:
                ev = self._cancel_events.setdefault(record.workspace_id, threading.Event())
                ev.set()
            elif scope_norm == "agent_global":
                for ev in self._cancel_events.values():
                    ev.set()

        self._record_local_event(
            workspace_id=record.workspace_id or "global",
            session_id=None,
            event_type="kill_switch",
            scout_verdict="blocked",
            scout_risk_score=1.0,
            extra={"scope": record.scope, "reason": record.reason, "activated_by": record.activated_by},
        )
        logger.warning(
            "Aiva Scout kill activated scope=%s workspace=%s by=%s",
            record.scope,
            record.workspace_id,
            record.activated_by,
        )
        return {
            "id": record.id,
            "active": True,
            "scope": record.scope,
            "workspace_id": record.workspace_id,
            "reason": record.reason,
            "activated_by": record.activated_by,
            "activated_at": _iso(record.activated_at),
        }

    def deactivate_kill(
        self,
        *,
        workspace_id: str | None = None,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """Clear active kills.

        - workspace_id set: clear that workspace's workspace-scope kills
        - scope=agent_global: clear global kills
        - neither: clear all active kills (emergency resume-all)
        """
        cleared = 0
        with self._lock:
            for record in self._kills:
                if record.deactivated_at is not None:
                    continue
                if workspace_id:
                    if record.scope == "workspace" and record.workspace_id == workspace_id:
                        record.deactivated_at = time.time()
                        cleared += 1
                        ev = self._cancel_events.get(workspace_id)
                        if ev:
                            ev.clear()
                    continue
                if scope == "agent_global":
                    if record.scope == "agent_global":
                        record.deactivated_at = time.time()
                        cleared += 1
                    continue
                # resume all
                record.deactivated_at = time.time()
                cleared += 1
            if not workspace_id and scope != "agent_global":
                for ev in self._cancel_events.values():
                    ev.clear()
            elif not workspace_id and scope == "agent_global":
                # Only clear cancel events if no workspace kills remain for that key
                for wid, ev in list(self._cancel_events.items()):
                    if not any(
                        k.deactivated_at is None and k.scope == "workspace" and k.workspace_id == wid
                        for k in self._kills
                    ):
                        # keep set if somehow still killed; otherwise leave
                        pass

        return {"cleared": cleared, "active_kills": self.list_active_kills()}

    def is_cancelled(self, workspace_id: str) -> bool:
        kill = self.check_kill(workspace_id)
        if kill.active:
            return True
        with self._lock:
            ev = self._cancel_events.get(workspace_id)
            return bool(ev and ev.is_set() and kill.active)

    def list_active_kills(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": k.id,
                    "workspace_id": k.workspace_id,
                    "scope": k.scope,
                    "reason": k.reason,
                    "activated_by": k.activated_by,
                    "activated_at": _iso(k.activated_at),
                }
                for k in self._kills
                if k.deactivated_at is None
            ]

    # ── Filter / events / heartbeat ──────────────────────────────────────────

    async def filter_prompt(
        self,
        *,
        workspace_id: str,
        prompt: str,
        session_id: str | None = None,
        model: str | None = None,
    ) -> FilterResult:
        kill = self.check_kill(workspace_id)
        if kill.active:
            return FilterResult(
                blocked=True,
                verdict="blocked",
                risk_score=1.0,
                reason=kill.reason or "Agent execution suspended by Scout.",
            )

        snippet = (prompt or "")[:500]
        prompt_hash = hashlib.sha256((prompt or "").encode("utf-8")).hexdigest()

        if not self.enabled:
            self._record_local_event(
                workspace_id=workspace_id,
                session_id=session_id,
                event_type="prompt_filter",
                model=model,
                prompt_hash=prompt_hash,
                prompt_snippet=snippet,
                scout_verdict="allowed",
                scout_risk_score=0.0,
            )
            return FilterResult(blocked=False, verdict="allowed", risk_score=0.0, reason="scout_disabled")

        agent_id = self.agent_id_for(workspace_id)
        try:
            data = await self._post(
                "/v1/prompts/filter",
                {
                    "prompt": prompt,
                    "agent_id": agent_id,
                    "metadata": {
                        "workspace_id": workspace_id,
                        "session_id": session_id,
                        "product": "keprix-aiva",
                        "sensors": [s["id"] for s in KEPRIX_SENSORS],
                    },
                },
            )
        except ScoutRemoteError as exc:
            if exc.code == "kill_switch":
                self.activate_kill(
                    workspace_id=workspace_id,
                    scope="workspace",
                    reason="Scout SaaS kill_switch",
                    activated_by="scout",
                )
                return FilterResult(blocked=True, verdict="blocked", risk_score=1.0, reason=str(exc))
            if self._strict:
                return FilterResult(blocked=True, verdict="blocked", risk_score=1.0, reason=str(exc))
            logger.warning("Scout filter unavailable (fail-open): %s", exc)
            return FilterResult(blocked=False, verdict="allowed", risk_score=0.0, reason="scout_unavailable")

        verdict = str(data.get("verdict") or "allowed").lower()
        blocked = bool(data.get("blocked")) or verdict == "blocked"
        risk = float(data.get("risk_score") or data.get("score") or (1.0 if blocked else 0.0))
        reason = str(data.get("reason") or data.get("message") or "")
        self._record_local_event(
            workspace_id=workspace_id,
            session_id=session_id,
            event_type="prompt_filter",
            model=model,
            prompt_hash=prompt_hash,
            prompt_snippet=snippet,
            scout_verdict=verdict if verdict else ("blocked" if blocked else "allowed"),
            scout_risk_score=risk,
        )
        return FilterResult(
            blocked=blocked,
            verdict=verdict if verdict else ("blocked" if blocked else "allowed"),
            risk_score=risk,
            reason=reason,
            raw=data if isinstance(data, dict) else {},
        )

    async def log_event(
        self,
        *,
        workspace_id: str,
        event_type: str,
        session_id: str | None = None,
        model: str | None = None,
        tool_name: str | None = None,
        tool_args: Any = None,
        tool_result: Any = None,
        response: str | None = None,
        scout_verdict: str = "allowed",
        scout_risk_score: float = 0.0,
    ) -> dict[str, Any]:
        anomaly = self._detect_tool_anomaly(workspace_id, tool_name) if event_type == "tool_call" else None
        if anomaly:
            scout_verdict = "flagged"
            scout_risk_score = max(scout_risk_score, 0.8)
            self._record_local_event(
                workspace_id=workspace_id,
                session_id=session_id,
                event_type="anomaly",
                model=model,
                tool_name=tool_name,
                scout_verdict="flagged",
                scout_risk_score=scout_risk_score,
                extra=anomaly,
            )

        local = self._record_local_event(
            workspace_id=workspace_id,
            session_id=session_id,
            event_type=event_type,
            model=model,
            tool_name=tool_name,
            tool_args_json=_safe_json_snippet(tool_args),
            tool_result_snippet=_snippet(tool_result),
            response_snippet=_snippet(response),
            scout_verdict=scout_verdict,
            scout_risk_score=scout_risk_score,
        )

        if not self.enabled:
            return {"ok": True, "local": True, "event": local, "anomaly": anomaly}

        agent_id = self.agent_id_for(workspace_id)
        remote_type = {
            "tool_call": "tool_call_completed",
            "agent_response": "agent_response",
            "prompt_filter": "prompt_filter",
            "anomaly": "anomaly",
            "kill_switch": "kill_switch",
        }.get(event_type, event_type)

        try:
            remote = await self._post(
                "/v1/events",
                {
                    "agent_id": agent_id,
                    "event_type": remote_type,
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "tool_result": _snippet(tool_result, 2000),
                    "session_id": session_id,
                    "metadata": {
                        "workspace_id": workspace_id,
                        "model": model,
                        "response_snippet": _snippet(response),
                        "sensors": [s["id"] for s in KEPRIX_SENSORS],
                        "anomaly": anomaly,
                    },
                },
            )
            return {"ok": True, "event": local, "remote": remote, "anomaly": anomaly}
        except ScoutRemoteError as exc:
            if exc.code == "kill_switch":
                self.activate_kill(
                    workspace_id=workspace_id,
                    scope="workspace",
                    reason="Scout SaaS kill_switch on event",
                    activated_by="scout",
                )
            logger.warning("Scout event log failed: %s", exc)
            return {"ok": False, "event": local, "error": str(exc), "anomaly": anomaly}

    async def heartbeat(self, *, workspace_id: str | None = None) -> dict[str, Any]:
        payload = {
            "product": os.environ.get("KEPRIX_SCOUT_PRODUCT", "keprix"),
            "workspace_id": workspace_id,
            "sensors": list(KEPRIX_SENSORS),
            "kills": self.list_active_kills(),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        if not self.enabled:
            return {"ok": True, "disabled": True, **payload}
        try:
            # Prefer SaaS health; fall back to agent status when agent id configured.
            health = await self._get("/v1/health")
            status = None
            if workspace_id:
                try:
                    status = await self._get(f"/v1/agents/{self.agent_id_for(workspace_id)}/status")
                except ScoutRemoteError:
                    status = None
            return {"ok": True, "health": health, "agent_status": status, **payload}
        except ScoutRemoteError as exc:
            return {"ok": False, "error": str(exc), **payload}

    def sensors(self) -> list[dict[str, str]]:
        return [dict(s) for s in KEPRIX_SENSORS]

    def recent_events(self, *, workspace_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self._events)
        if workspace_id:
            rows = [r for r in rows if r.get("workspace_id") == workspace_id]
        return rows[-limit:]

    def reset_for_tests(self) -> None:
        with self._lock:
            self._kills.clear()
            self._cancel_events.clear()
            self._events.clear()
            self._tool_counts.clear()

    # ── HTTP ─────────────────────────────────────────────────────────────────

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Product": os.environ.get("KEPRIX_SCOUT_PRODUCT", "keprix"),
        }
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
        except Exception as exc:
            raise ScoutRemoteError(str(exc), code="network") from exc
        return self._parse_response(resp)

    async def _get(self, path: str) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "X-Product": os.environ.get("KEPRIX_SCOUT_PRODUCT", "keprix"),
        }
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout) as client:
                resp = await client.get(url, headers=headers)
        except Exception as exc:
            raise ScoutRemoteError(str(exc), code="network") from exc
        return self._parse_response(resp)

    def _parse_response(self, resp: httpx.Response) -> dict[str, Any]:
        body: Any
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:500]}
        if resp.status_code == 403:
            err = body.get("error") if isinstance(body, dict) else None
            if err == "kill_switch" or (isinstance(body, dict) and body.get("code") == "kill_switch"):
                raise ScoutRemoteError("Scout kill_switch", status=403, code="kill_switch", body=body)
        if resp.status_code >= 400:
            raise ScoutRemoteError(
                f"Scout HTTP {resp.status_code}",
                status=resp.status_code,
                code="http_error",
                body=body,
            )
        return body if isinstance(body, dict) else {"data": body}

    def _detect_tool_anomaly(self, workspace_id: str, tool_name: str | None) -> dict[str, Any] | None:
        if not tool_name:
            return None
        key = f"{workspace_id}:{tool_name}"
        now = time.time()
        window = 60.0
        limit = int(os.environ.get("KEPRIX_SCOUT_TOOL_BURST_LIMIT", "40"))
        with self._lock:
            stamps = [t for t in self._tool_counts.get(key, []) if now - t <= window]
            stamps.append(now)
            self._tool_counts[key] = stamps
            if len(stamps) >= limit:
                return {
                    "sensor": "keprix_tool_sensor",
                    "tool_name": tool_name,
                    "count": len(stamps),
                    "window_seconds": window,
                    "message": f"Tool burst: {tool_name} called {len(stamps)} times in {int(window)}s",
                }
        return None

    def _record_local_event(
        self,
        *,
        workspace_id: str,
        session_id: str | None,
        event_type: str,
        model: str | None = None,
        prompt_hash: str | None = None,
        prompt_snippet: str | None = None,
        tool_name: str | None = None,
        tool_args_json: str | None = None,
        tool_result_snippet: str | None = None,
        response_snippet: str | None = None,
        scout_verdict: str = "allowed",
        scout_risk_score: float = 0.0,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "session_id": session_id,
            "event_type": event_type,
            "model": model,
            "prompt_hash": prompt_hash,
            "prompt_snippet": prompt_snippet,
            "tool_name": tool_name,
            "tool_args_json": tool_args_json,
            "tool_result_snippet": tool_result_snippet,
            "response_snippet": response_snippet,
            "scout_verdict": scout_verdict,
            "scout_risk_score": scout_risk_score,
            "extra": extra or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._events.append(row)
            if len(self._events) > 5000:
                self._events = self._events[-2500:]
        return row


class ScoutRemoteError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status: int = 0,
        code: str = "error",
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.body = body


_guard: AivaScoutGuard | None = None
_guard_lock = threading.Lock()


def get_aiva_scout_guard() -> AivaScoutGuard:
    global _guard
    with _guard_lock:
        if _guard is None:
            _guard = AivaScoutGuard()
        return _guard


def set_aiva_scout_guard(guard: AivaScoutGuard | None) -> None:
    global _guard
    with _guard_lock:
        _guard = guard


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _snippet(value: Any, limit: int = 500) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value[:limit]
    try:
        import json

        return json.dumps(value, default=str)[:limit]
    except Exception:
        return str(value)[:limit]


def _safe_json_snippet(value: Any, limit: int = 2000) -> str | None:
    return _snippet(value, limit)
