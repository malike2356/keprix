"""Configuration for LLM usage recording."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LlmUsageConfig:
    enabled: bool
    retention_days: int
    sqlite_fallback: bool


def get_llm_usage_config() -> LlmUsageConfig:
    enabled = os.getenv("KEPRIX_LLM_USAGE_ENABLED", "true").lower() in {"1", "true", "yes"}
    try:
        retention_days = int(os.getenv("KEPRIX_LLM_USAGE_RETENTION_DAYS", "90"))
    except ValueError:
        retention_days = 90
    sqlite_fallback = os.getenv("KEPRIX_LLM_USAGE_SQLITE_FALLBACK", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    return LlmUsageConfig(
        enabled=enabled,
        retention_days=max(1, retention_days),
        sqlite_fallback=sqlite_fallback,
    )
