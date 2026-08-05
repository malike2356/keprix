"""Keprix to Scout signal client with batched, fire-and-forget delivery."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from keprix.governance.signing import sign_payload
from keprix.security.scout_config import ScoutConfig, resolve_scout_config
from keprix.security.scout_types import ScoutSignal, SignalCategory, SignalSeverity

logger = logging.getLogger(__name__)

FLUSH_INTERVAL = 0.5
MAX_BUFFER_SIZE = 50
MAX_RETRY_BUFFER = 1000
HEARTBEAT_INTERVAL = 30.0


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _redact_details(details: dict[str, Any]) -> dict[str, Any]:
    from keprix.security.audit import _strip_secrets

    return _strip_secrets(details)


class ScoutClient:
    """Buffers security signals and flushes them to Scout in batches."""

    def __init__(self, config: ScoutConfig) -> None:
        self._config = config
        self._buffer: list[ScoutSignal] = []
        self._lock = threading.Lock()
        self._flush_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None
        self._client: httpx.AsyncClient | None = None

    @property
    def enabled(self) -> bool:
        return self._config.enabled and bool(self._config.api_key)

    async def start(self) -> None:
        if not self.enabled:
            return
        if self._flush_task is not None and not self._flush_task.done():
            return
        self._stop_event = asyncio.Event()
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        if self._config.agent_id:
            headers["X-Agent-Id"] = self._config.agent_id
        headers["X-Product"] = self._config.product
        self._client = httpx.AsyncClient(timeout=5.0, headers=headers)
        self._flush_task = asyncio.create_task(self._flush_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        for task in (self._flush_task, self._heartbeat_task):
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        await self._flush()
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._flush_task = None
        self._heartbeat_task = None
        self._stop_event = None

    def send(
        self,
        category: SignalCategory,
        severity: SignalSeverity,
        action: str,
        target: str,
        details: dict[str, Any] | None = None,
        *,
        correlation_id: str | None = None,
        threat_score: float | None = None,
    ) -> None:
        """Queue a signal. Non-blocking. Never raises."""
        if not self.enabled:
            return
        agent_id = self._config.agent_id or "keprix:local"
        signal = ScoutSignal(
            signal_id=_new_uuid(),
            timestamp=_utc_now(),
            agent_id=agent_id,
            product=self._config.product,
            category=category,
            severity=severity,
            action=action,
            target=target,
            details=_redact_details(details or {}),
            correlation_id=correlation_id,
            threat_score=threat_score,
        )
        with self._lock:
            self._buffer.append(signal)
            if len(self._buffer) > MAX_RETRY_BUFFER:
                self._buffer.pop(0)
        self._mirror_to_governance(signal)

    def pending_count(self) -> int:
        with self._lock:
            return len(self._buffer)

    def _mirror_to_governance(self, signal: ScoutSignal) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._queue_governance(signal))

    async def _queue_governance(self, signal: ScoutSignal) -> None:
        try:
            from keprix.governance.event_reporter import queue_audit_event

            await queue_audit_event("scout_signal", self._serialize(signal))
        except Exception:
            logger.debug("scout signal governance mirror skipped", exc_info=True)

    async def _flush_loop(self) -> None:
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=FLUSH_INTERVAL)
            except TimeoutError:
                pass
            if self.pending_count():
                await self._flush()

    async def _heartbeat_loop(self) -> None:
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            self.send(
                SignalCategory.HEARTBEAT,
                SignalSeverity.INFO,
                "heartbeat",
                f"agent:{self._config.agent_id or 'local'}",
                details={"product": self._config.product},
            )
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=HEARTBEAT_INTERVAL)
            except TimeoutError:
                pass

    async def _flush(self) -> None:
        if self._client is None or not self._config.api_key:
            return
        with self._lock:
            if not self._buffer:
                return
            batch = self._buffer[:MAX_BUFFER_SIZE]
            payload_signals = [self._serialize(signal) for signal in batch]
        body = json.dumps(
            {
                "instance_id": self._config.agent_id,
                "signals": payload_signals,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        signature = sign_payload(self._config.api_key, body)
        headers = {"X-Governance-Signature": f"sha256={signature}"}
        try:
            response = await self._client.post(
                self._config.signals_url,
                content=body,
                headers=headers,
            )
            if response.status_code < 400:
                with self._lock:
                    self._buffer = self._buffer[len(batch) :]
            else:
                logger.warning(
                    "scout signal flush failed status=%s body=%s",
                    response.status_code,
                    response.text[:200],
                )
        except Exception:
            logger.debug("scout signal flush unreachable", exc_info=True)

    @staticmethod
    def _serialize(signal: ScoutSignal) -> dict[str, Any]:
        return {
            "signal_id": signal.signal_id,
            "timestamp": signal.timestamp,
            "agent_id": signal.agent_id,
            "product": signal.product,
            "category": signal.category.value,
            "severity": signal.severity.value,
            "action": signal.action,
            "target": signal.target,
            "details": signal.details,
            "mitre_tactic": signal.mitre_tactic,
            "threat_score": signal.threat_score,
            "correlation_id": signal.correlation_id,
        }


_client: ScoutClient | None = None


async def _resolve_runtime_config() -> ScoutConfig:
    agent_id: str | None = None
    try:
        from keprix.governance.store import get_governance_store

        cfg = await get_governance_store().get_config()
        agent_id = str(cfg.get("instance_id") or "") or None
    except Exception:
        agent_id = None
    product = "keprix"
    try:
        from keprix.security.product_context import get_product_context_or_none

        ctx = get_product_context_or_none()
        if ctx is not None:
            product = ctx.product_id
    except Exception:
        pass
    return resolve_scout_config(agent_id=agent_id, product=product)


def get_scout_client() -> ScoutClient:
    global _client
    if _client is None:
        _client = ScoutClient(resolve_scout_config())
    return _client


async def refresh_scout_client() -> ScoutClient:
    global _client
    config = await _resolve_runtime_config()
    if _client is None:
        _client = ScoutClient(config)
    else:
        _client._config = config
    return _client


def reset_scout_client() -> None:
    global _client
    _client = None
