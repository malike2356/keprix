"""Migrate credentials from Keprix .env into proxy routes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from keprix.proxy.config import ProxyConfig, RouteConfig, dump_proxy_config, load_proxy_config
from keprix.proxy.paths import keprix_home, local_vault_path


ENV_TO_ROUTE = {
    "ANTHROPIC_API_KEY": ("api.anthropic.com", "x-api-key", "anthropic-api-key", None),
    "OPENAI_API_KEY": ("api.openai.com", "Authorization", "openai-api-key", "Bearer"),
    "GEMINI_API_KEY": ("generativelanguage.googleapis.com", "x-goog-api-key", "gemini-api-key", None),
    "GOOGLE_API_KEY": ("generativelanguage.googleapis.com", "x-goog-api-key", "gemini-api-key", None),
}


@dataclass
class MigrationResult:
    migrated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def migrate_vault_from_env(env_path: Path | None = None) -> MigrationResult:
    env_file = env_path or (keprix_home() / ".env")
    env_values = _read_env_file(env_file)
    result = MigrationResult()
    config = load_proxy_config()
    existing_hosts = {route.host for route in config.routes}

    local_path = local_vault_path()
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_data = {"secrets": {}}
    if local_path.is_file():
        local_data = json.loads(local_path.read_text(encoding="utf-8"))

    for env_key, (host, header_name, secret_ref, scheme) in ENV_TO_ROUTE.items():
        value = env_values.get(env_key, "")
        if not value or value.startswith("dummy-replaced-by-proxy"):
            result.skipped.append(env_key)
            continue
        local_data.setdefault("secrets", {})[secret_ref] = value
        if host not in existing_hosts:
            config.routes.append(
                RouteConfig(
                    host=host,
                    header_name=header_name,
                    secret_ref=secret_ref,
                    scheme=scheme,
                )
            )
            existing_hosts.add(host)
        result.migrated.append(env_key)

    local_path.write_text(json.dumps(local_data, indent=2) + "\n", encoding="utf-8")
    local_path.chmod(0o600)
    if config.vault != "keychain":
        config.vault = "keychain"
    dump_proxy_config(config)
    return result
