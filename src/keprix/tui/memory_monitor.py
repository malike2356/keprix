"""Memory usage monitoring for the TUI."""

from __future__ import annotations

from dataclasses import dataclass
import os
import resource


@dataclass(frozen=True)
class MemorySnapshot:
    rss_bytes: int
    pressure: str


def memory_snapshot() -> MemorySnapshot:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    multiplier = 1024 if os.name != "posix" else 1024
    rss = int(usage * multiplier)
    pressure = "high" if rss > 1_000_000_000 else "normal"
    return MemorySnapshot(rss_bytes=rss, pressure=pressure)

