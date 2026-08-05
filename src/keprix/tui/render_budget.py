"""Render budget helpers for smooth terminal updates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderBudget:
    target_fps: int = 60

    @property
    def frame_budget_ms(self) -> float:
        return 1000 / max(1, self.target_fps)

    def over_budget(self, frame_time_ms: float) -> bool:
        return frame_time_ms > self.frame_budget_ms

