"""Regression detection: flag providers whose quality scores drop significantly."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ScoreRecord:
    provider: str
    score: float
    label: str
    at: float = field(default_factory=time.time)


@dataclass
class RegressionAlert:
    provider: str
    baseline_avg: float
    recent_avg: float
    drop_pct: float
    window_size: int
    at: float = field(default_factory=time.time)


class RegressionDetector:
    """Compare recent quality scores against a baseline to detect regressions.

    Uses a sliding window split into baseline (older half) and recent (newer half).
    Fires a regression alert when the recent average drops by more than
    ``threshold_pct`` below the baseline.

    Usage::

        detector = RegressionDetector(window=100, threshold_pct=0.15)
        detector.record(ScoreRecord(provider="openai", score=0.95, label="pass"))
        alert = detector.check("openai")
        if alert:
            logger.warning("Regression on openai: %.0f%% drop", alert.drop_pct * 100)
    """

    def __init__(self, window: int = 100, threshold_pct: float = 0.15) -> None:
        self._window = window
        self._threshold = threshold_pct
        self._records: dict[str, deque[ScoreRecord]] = {}
        self._lock = asyncio.Lock()

    def record(self, rec: ScoreRecord) -> None:
        if rec.provider not in self._records:
            self._records[rec.provider] = deque(maxlen=self._window)
        self._records[rec.provider].append(rec)

    def check(self, provider: str) -> RegressionAlert | None:
        """Return a RegressionAlert if regression detected, else None."""
        records = list(self._records.get(provider, []))
        n = len(records)
        if n < 20:
            return None  # not enough data

        mid = n // 2
        baseline = records[:mid]
        recent = records[mid:]

        baseline_avg = sum(r.score for r in baseline) / len(baseline)
        recent_avg = sum(r.score for r in recent) / len(recent)

        if baseline_avg == 0:
            return None

        drop = (baseline_avg - recent_avg) / baseline_avg
        if drop >= self._threshold:
            return RegressionAlert(
                provider=provider,
                baseline_avg=round(baseline_avg, 4),
                recent_avg=round(recent_avg, 4),
                drop_pct=round(drop, 4),
                window_size=n,
            )
        return None

    def check_all(self) -> list[RegressionAlert]:
        """Check all registered providers for regressions."""
        alerts = []
        for provider in list(self._records):
            alert = self.check(provider)
            if alert:
                alerts.append(alert)
        return alerts

    def recent_average(self, provider: str, last_n: int = 10) -> float | None:
        """Return the average score of the last ``last_n`` records."""
        records = list(self._records.get(provider, []))
        if not records:
            return None
        window = records[-last_n:]
        return sum(r.score for r in window) / len(window)
