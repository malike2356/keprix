"""LLM provider registry with health-check probes for self-configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from keprix_cli.models import _KEPRIX_USER_AGENT


@dataclass
class ProviderProbe:
    name: str
    supports_health_check: bool = True

    async def health_check(self, client: httpx.AsyncClient) -> None:
        if not self.supports_health_check:
            return
        from keprix_cli.auth import PROVIDER_REGISTRY

        config = PROVIDER_REGISTRY.get(self.name)
        if config is None:
            raise RuntimeError(f"unknown provider: {self.name}")

        key = ""
        for env_var in config.api_key_env_vars:
            key = os.environ.get(env_var, "")
            if key:
                break
        if not key:
            raise RuntimeError("no API key configured")

        base_env = getattr(config, "base_url_env", None) or ""
        base = os.environ.get(base_env, "") if base_env else ""
        default_url = getattr(config, "default_base_url", "") or ""
        if not base and default_url:
            url = default_url.rstrip("/") + "/models"
        elif base:
            url = base.rstrip("/") + "/models"
        else:
            url = default_url

        if not url:
            return

        headers = {"Authorization": f"Bearer {key}", "User-Agent": _KEPRIX_USER_AGENT}
        response = await client.get(url, headers=headers)
        if response.status_code == 401:
            raise RuntimeError("invalid API key")
        if response.status_code >= 500:
            raise RuntimeError(f"provider returned HTTP {response.status_code}")


def iter_configured_providers() -> list[ProviderProbe]:
    """Return providers that have at least one API key env var set."""
    from keprix_cli.auth import PROVIDER_REGISTRY

    probes: list[ProviderProbe] = []
    seen: set[str] = set()
    for name, config in PROVIDER_REGISTRY.items():
        if name in seen:
            continue
        seen.add(name)
        has_key = any(os.environ.get(var, "") for var in config.api_key_env_vars)
        if not has_key:
            continue
        supports = getattr(config, "supports_health_check", True)
        probes.append(ProviderProbe(name=name, supports_health_check=supports))
    return probes
