"""Write proxy environment variables for Keprix runtime."""

from __future__ import annotations

import os
from pathlib import Path

from keprix.proxy.certs import ensure_ca_material
from keprix.proxy.config import ProxyConfig
from keprix.proxy.paths import keprix_home, proxy_env_marker_path


DUMMY_KEYS = {
    "ANTHROPIC_API_KEY": "dummy-replaced-by-proxy",
    "OPENAI_API_KEY": "dummy-replaced-by-proxy",
    "GEMINI_API_KEY": "dummy-replaced-by-proxy",
    "GOOGLE_API_KEY": "dummy-replaced-by-proxy",
}


def proxy_env_vars(config: ProxyConfig) -> dict[str, str]:
    ca_cert, _ = ensure_ca_material()
    listen = config.listen
    if "://" not in listen:
        listen = f"http://{listen}"
    return {
        "HTTP_PROXY": listen,
        "HTTPS_PROXY": listen,
        "http_proxy": listen,
        "https_proxy": listen,
        "SSL_CERT_FILE": str(ca_cert),
        "REQUESTS_CA_BUNDLE": str(ca_cert),
        **DUMMY_KEYS,
    }


def write_proxy_env(config: ProxyConfig, env_path: Path | None = None) -> Path:
    target = env_path or (keprix_home() / ".env")
    existing: dict[str, str] = {}
    if target.is_file():
        for line in target.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            existing[key.strip()] = value.strip()

    merged = {**existing, **proxy_env_vars(config)}
    lines = [f"{key}={value}" for key, value in sorted(merged.items())]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    proxy_env_marker_path().write_text(str(target), encoding="utf-8")
    return target


def print_proxy_env(config: ProxyConfig) -> str:
    return "\n".join(f'export {key}="{value}"' for key, value in proxy_env_vars(config).items())
