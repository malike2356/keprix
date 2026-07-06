"""Telemetry store for the config optimizer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TelemetryStore(Protocol):
    async def fetch_provider_stats(self, days: int = 7) -> dict[str, dict[str, Any]]: ...

    async def fetch_memory_stats(self, days: int = 7) -> dict[str, Any]: ...

    async def fetch_channel_stats(self, days: int = 7) -> dict[str, dict[str, Any]]: ...


class JsonlTelemetryStore:
    """Read telemetry aggregates from a JSONL file (used in tests and local installs)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _read_rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.path.open() as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    async def fetch_provider_stats(self, days: int = 7) -> dict[str, dict[str, Any]]:
        del days
        stats: dict[str, dict[str, Any]] = {}
        for row in self._read_rows():
            if row.get("kind") != "provider":
                continue
            provider = str(row["provider"])
            stats[provider] = {
                "error_rate": float(row.get("error_rate", 0)),
                "call_count": int(row.get("call_count", 0)),
                "error_count": int(row.get("error_count", 0)),
                "next_best_provider": row.get("next_best_provider"),
            }
        return stats

    async def fetch_memory_stats(self, days: int = 7) -> dict[str, Any]:
        del days
        for row in self._read_rows():
            if row.get("kind") == "memory":
                return {
                    "legitimate_drop_rate": float(row.get("legitimate_drop_rate", 0)),
                    "current_limit": int(row.get("current_limit", 50)),
                }
        return {"legitimate_drop_rate": 0.0, "current_limit": 50}

    async def fetch_channel_stats(self, days: int = 7) -> dict[str, dict[str, Any]]:
        del days
        stats: dict[str, dict[str, Any]] = {}
        for row in self._read_rows():
            if row.get("kind") != "channel":
                continue
            channel = str(row["channel"])
            stats[channel] = {
                "message_count": int(row.get("message_count", 0)),
                "enabled": bool(row.get("enabled", True)),
            }
        return stats
