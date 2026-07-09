"""Interactive setup wizard for credential proxy."""

from __future__ import annotations

import json
import os
from pathlib import Path

from keprix.proxy.config import ProxyConfig, RouteConfig, dump_proxy_config
from keprix.proxy.env_writer import write_proxy_env
from keprix.proxy.paths import local_vault_path
from keprix.proxy.vault import get_vault_provider

DEFAULT_PROVIDER_ROUTES = [
    ("api.anthropic.com", "x-api-key", "anthropic-api-key", None),
    ("api.openai.com", "Authorization", "openai-api-key", "Bearer"),
    ("generativelanguage.googleapis.com", "x-goog-api-key", "gemini-api-key", None),
]


def detect_vault_provider() -> str:
    for name in ("bitwarden", "onepassword", "keychain"):
        if get_vault_provider(name).is_available():
            return name
    return "keychain"


def _ensure_local_vault() -> None:
    path = local_vault_path()
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"secrets": {}}, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _seed_local_secret(secret_ref: str, env_var: str) -> None:
    value = os.environ.get(env_var, "").strip()
    if not value:
        return
    path = local_vault_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    secrets = data.setdefault("secrets", {})
    secrets[secret_ref] = value
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run_setup_wizard(*, vault: str | None = None, interactive: bool = True) -> ProxyConfig:
    _ensure_local_vault()
    chosen_vault = vault or detect_vault_provider()
    routes: list[RouteConfig] = []

    for host, header_name, secret_ref, scheme in DEFAULT_PROVIDER_ROUTES:
        env_map = {
            "anthropic-api-key": "ANTHROPIC_API_KEY",
            "openai-api-key": "OPENAI_API_KEY",
            "gemini-api-key": "GEMINI_API_KEY",
        }
        if chosen_vault == "keychain":
            _seed_local_secret(secret_ref, env_map.get(secret_ref, ""))
        routes.append(
            RouteConfig(
                host=host,
                header_name=header_name,
                secret_ref=secret_ref,
                scheme=scheme,
            )
        )

    config = ProxyConfig(listen="127.0.0.1:6790", vault=chosen_vault, routes=routes)
    dump_proxy_config(config)
    write_proxy_env(config)
    return config
