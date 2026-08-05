"""Cordon compatibility helpers for the Keprix credential proxy contract."""

from __future__ import annotations

import os
import socket
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from keprix.config.health_monitor import ComponentHealth
from keprix.proxy.config import RouteConfig
from keprix.proxy.pidfile import is_running as keprix_proxy_running


PROVIDER_ROUTES: tuple[RouteConfig, ...] = (
    RouteConfig(host="api.anthropic.com", header_name="x-api-key", secret_ref="anthropic-api-key"),
    RouteConfig(host="api.openai.com", header_name="Authorization", scheme="Bearer", secret_ref="openai-api-key"),
    RouteConfig(host="generativelanguage.googleapis.com", header_name="x-goog-api-key", secret_ref="gemini-api-key"),
    RouteConfig(host="api.deepseek.com", header_name="Authorization", scheme="Bearer", secret_ref="deepseek-api-key"),
    RouteConfig(host="api.groq.com", header_name="Authorization", scheme="Bearer", secret_ref="groq-api-key"),
    RouteConfig(host="openrouter.ai", header_name="Authorization", scheme="Bearer", secret_ref="openrouter-api-key"),
    RouteConfig(host="api.mistral.ai", header_name="Authorization", scheme="Bearer", secret_ref="mistral-api-key"),
    RouteConfig(host="api.together.xyz", header_name="Authorization", scheme="Bearer", secret_ref="together-api-key"),
    RouteConfig(host="api.fireworks.ai", header_name="Authorization", scheme="Bearer", secret_ref="fireworks-api-key"),
    RouteConfig(host="api.x.ai", header_name="Authorization", scheme="Bearer", secret_ref="xai-api-key"),
)


def render_cordon_template(routes: tuple[RouteConfig, ...] = PROVIDER_ROUTES) -> str:
    lines = [
        "[proxy]",
        'listen = "127.0.0.1:6790"',
        'vault = "1password"',
        'log_level = "warn"',
        "",
    ]
    for route in routes:
        lines.extend(
            [
                "[[routes]]",
                f'host = "{route.host}"',
                f'header_name = "{route.header_name}"',
                'type = "header"',
                f'secret_ref = "{route.secret_ref}"',
            ]
        )
        if route.scheme:
            lines.append(f'scheme = "{route.scheme}"')
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def proxy_env_contract(proxy_url: str = "http://127.0.0.1:6790") -> dict[str, str]:
    return {
        "HTTP_PROXY": proxy_url,
        "HTTPS_PROXY": proxy_url,
        "ANTHROPIC_API_KEY": "dummy-replaced-by-proxy",
        "OPENAI_API_KEY": "dummy-replaced-by-proxy",
        "GOOGLE_API_KEY": "dummy-replaced-by-proxy",
    }


@dataclass(frozen=True)
class CordonHealthCheck:
    """Check that Cordon or keprix-proxy is available through the proxy env contract."""

    proxy_url: str | None = None

    async def check(self) -> ComponentHealth:
        started = time.monotonic()
        proxy = self.proxy_url or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
        if not proxy:
            if keprix_proxy_running():
                return ComponentHealth("credential-proxy", "healthy", (time.monotonic() - started) * 1000, "keprix-proxy pid is running", time.time())
            return ComponentHealth("credential-proxy", "degraded", 0, "HTTPS_PROXY is not set and keprix-proxy is not running", time.time())
        parsed = urlparse(proxy)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            with socket.create_connection((host, port), timeout=1.0):
                pass
            status = "healthy"
            error = ""
        except OSError as exc:
            status = "down"
            error = str(exc)
        return ComponentHealth("credential-proxy", status, (time.monotonic() - started) * 1000, error, time.time())


def provider_route_table() -> list[dict[str, Any]]:
    return [
        {
            "host": route.host,
            "header_name": route.header_name,
            "scheme": route.scheme,
            "secret_ref": route.secret_ref,
        }
        for route in PROVIDER_ROUTES
    ]
