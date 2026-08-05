"""Environment configuration for Scout integration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ScoutConfig:
    enabled: bool
    api_key: str | None
    endpoint: str
    redis_url: str | None
    agent_id: str | None
    product: str

    @property
    def signals_url(self) -> str:
        base = self.endpoint.rstrip("/")
        if base.endswith("/api/v1/signals"):
            return base
        return f"{base}/api/v1/signals"

    @property
    def sync_url(self) -> str:
        base = self.endpoint.rstrip("/")
        if base.endswith("/api/v1/compliance/sync"):
            return base
        return f"{base}/api/v1/compliance/sync"


def resolve_scout_config(
    *,
    agent_id: str | None = None,
    product: str | None = None,
) -> ScoutConfig:
    file_cfg: dict[str, Any] = {}
    try:
        from keprix_cli.config import load_config

        raw = load_config().get("scout") or {}
        if isinstance(raw, dict):
            file_cfg = raw
    except Exception:
        file_cfg = {}

    api_key = (
        os.environ.get("SCOUT_API_KEY")
        or os.environ.get("KEPRIX_GOVERNANCE_API_KEY")
        or os.environ.get("LABYRINTH_SCOUT_API_KEY")
        or file_cfg.get("api_key")
    )
    endpoint = (
        os.environ.get("SCOUT_ENDPOINT")
        or os.environ.get("KEPRIX_GOVERNANCE_ENDPOINT")
        or file_cfg.get("endpoint")
        or "https://console.labyrinthscout.com"
    )
    redis_url = os.environ.get("SCOUT_REDIS_URL") or file_cfg.get("redis_url")
    enabled = (
        _truthy(os.environ.get("SCOUT_ENABLED"))
        or _truthy(os.environ.get("KEPRIX_GOVERNANCE_ENABLED"))
        or bool(file_cfg.get("enabled"))
    )
    if api_key and endpoint:
        enabled = True
    return ScoutConfig(
        enabled=enabled and bool(api_key),
        api_key=str(api_key) if api_key else None,
        endpoint=str(endpoint),
        redis_url=str(redis_url) if redis_url else None,
        agent_id=agent_id or file_cfg.get("agent_id"),
        product=product or file_cfg.get("product") or os.environ.get("KEPRIX_SCOUT_PRODUCT", "keprix"),
    )
