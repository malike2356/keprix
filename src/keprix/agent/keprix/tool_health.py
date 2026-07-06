"""Health monitoring and quarantine for generated tools."""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Deque

logger = logging.getLogger(__name__)

_QUARANTINED: set[str] = set()


class ToolHealthMonitor:
    def __init__(self, error_threshold: float = 0.10, window_seconds: int = 300) -> None:
        self.error_threshold = error_threshold
        self.window_seconds = window_seconds
        self._calls: Deque[tuple[float, bool]] = deque()

    def record(self, success: bool) -> None:
        now = time.time()
        self._calls.append((now, success))
        cutoff = now - self.window_seconds
        while self._calls and self._calls[0][0] < cutoff:
            self._calls.popleft()

    def error_rate(self) -> float:
        if not self._calls:
            return 0.0
        errors = sum(1 for _, ok in self._calls if not ok)
        return errors / len(self._calls)

    def should_quarantine(self) -> bool:
        return len(self._calls) >= 10 and self.error_rate() > self.error_threshold


_monitors: dict[str, ToolHealthMonitor] = {}


def get_tool_health_monitor(tool_name: str) -> ToolHealthMonitor:
    if tool_name not in _monitors:
        _monitors[tool_name] = ToolHealthMonitor()
    return _monitors[tool_name]


def is_quarantined(tool_name: str) -> bool:
    return tool_name in _QUARANTINED


async def quarantine_tool(tool_name: str) -> None:
    _QUARANTINED.add(tool_name)
    logger.warning("Quarantined generated tool: %s", tool_name)
    try:
        from keprix.security.event_reporter import report_security_event

        monitor = get_tool_health_monitor(tool_name)
        await report_security_event(
            "tool_quarantined",
            severity="high",
            data={"tool": tool_name, "error_rate": monitor.error_rate()},
        )
    except Exception:
        pass


def record_tool_result(tool_name: str, success: bool) -> None:
    if tool_name in _QUARANTINED:
        return
    monitor = get_tool_health_monitor(tool_name)
    monitor.record(success)
    if monitor.should_quarantine():
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(quarantine_tool(tool_name))
        except RuntimeError:
            pass
