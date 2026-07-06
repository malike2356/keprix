"""LLM usage event schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid


@dataclass
class LlmUsageRecord:
    workspace_id: str = "default"
    user_id: str | None = None
    session_id: str | None = None
    run_id: str | None = None
    channel: str = "unknown"
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    cost_usd: Decimal | None = None
    cost_status: str = "unknown"
    cost_source: str = "none"
    duration_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_row(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "recorded_at": self.recorded_at,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "channel": self.channel,
            "provider": self.provider or "",
            "model": self.model or "",
            "input_tokens": int(self.input_tokens),
            "output_tokens": int(self.output_tokens),
            "cache_read_tokens": int(self.cache_read_tokens),
            "cache_write_tokens": int(self.cache_write_tokens),
            "reasoning_tokens": int(self.reasoning_tokens),
            "total_tokens": int(self.total_tokens),
            "cost_usd": float(self.cost_usd) if self.cost_usd is not None else None,
            "cost_status": self.cost_status,
            "cost_source": self.cost_source,
            "duration_ms": self.duration_ms,
            "metadata": dict(self.metadata or {}),
        }
