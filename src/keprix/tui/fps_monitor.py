"""Frame-rate monitoring helpers."""

from __future__ import annotations

import time
from collections import deque


class FpsMonitor:
    def __init__(self, max_samples: int = 120) -> None:
        self._frames: deque[float] = deque(maxlen=max_samples)

    def frame(self, now: float | None = None) -> None:
        self._frames.append(time.perf_counter() if now is None else now)

    @property
    def fps(self) -> float:
        if len(self._frames) < 2:
            return 0.0
        elapsed = self._frames[-1] - self._frames[0]
        return 0.0 if elapsed <= 0 else (len(self._frames) - 1) / elapsed

    def histogram_ms(self) -> list[float]:
        return [(b - a) * 1000 for a, b in zip(self._frames, list(self._frames)[1:])]

