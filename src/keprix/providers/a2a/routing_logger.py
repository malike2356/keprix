"""Structured routing logger for A2A observability: NDJSON sink for all route events."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RouteEvent:
    """One routing decision emitted per request."""
    timestamp: float
    request_id: str
    task_id: str
    combo_id: str
    selected_provider: str
    selected_model: str
    tier_id: str
    strategy: str
    latency_ms: float
    success: bool
    tried_providers: list[str] = field(default_factory=list)
    compression_savings_pct: float = 0.0
    pii_masked: bool = False
    injection_detected: bool = False
    token_usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class RoutingLogger:
    """Append structured route events to an NDJSON file for offline analysis.

    Sinks to a daily file. Suitable for piping into your analytics stack.

    Usage::

        rlog = RoutingLogger("logs/routing")
        rlog.emit(RouteEvent(
            timestamp=time.time(),
            request_id="abc",
            task_id="",
            combo_id="default",
            selected_provider="anthropic",
            selected_model="claude-haiku-4-5",
            tier_id="premium",
            strategy="balanced",
            latency_ms=342.1,
            success=True,
        ))
    """

    def __init__(self, directory: str | Path = "logs/routing") -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self) -> Path:
        import datetime
        return self._dir / f"routing-{datetime.date.today().isoformat()}.ndjson"

    def emit(self, event: RouteEvent) -> None:
        """Write a route event synchronously (fire-and-forget in async contexts)."""
        line = json.dumps(asdict(event), separators=(",", ":")) + "\n"
        try:
            with open(self._path(), "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError as exc:
            logger.error("RoutingLogger write failed: %s", exc)

    def emit_from_selection(
        self,
        *,
        request_id: str,
        task_id: str = "",
        combo_id: str,
        provider: str,
        model: str,
        tier_id: str,
        strategy: str,
        latency_ms: float,
        success: bool,
        tried: list[str] | None = None,
        compression_savings_pct: float = 0.0,
        pii_masked: bool = False,
        injection_detected: bool = False,
        token_usage: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Convenience wrapper: build and emit a RouteEvent in one call."""
        event = RouteEvent(
            timestamp=time.time(),
            request_id=request_id,
            task_id=task_id,
            combo_id=combo_id,
            selected_provider=provider,
            selected_model=model,
            tier_id=tier_id,
            strategy=strategy,
            latency_ms=latency_ms,
            success=success,
            tried_providers=tried or [],
            compression_savings_pct=compression_savings_pct,
            pii_masked=pii_masked,
            injection_detected=injection_detected,
            token_usage=token_usage or {},
            metadata=metadata or {},
        )
        self.emit(event)

    def tail(self, n: int = 50) -> list[RouteEvent]:
        """Return the last ``n`` events from today's log."""
        path = self._path()
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
        events = []
        for line in lines[-n:]:
            try:
                d = json.loads(line)
                events.append(RouteEvent(**d))
            except (json.JSONDecodeError, TypeError):
                pass
        return events
