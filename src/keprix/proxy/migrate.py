"""Migrate credentials from Keprix .env into proxy routes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.proxy.config import ProxyConfig, RouteConfig, dump_proxy_config, load_proxy_config
from keprix.proxy.paths import keprix_home, local_vault_path, migration_state_path


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
    verified: list[str] = field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _write_migration_state(result: MigrationResult, *, target_vault: str) -> None:
    state = {
        "updated_at": _now(),
        "target_vault": target_vault,
        "migrated": result.migrated,
        "verified": result.verified,
        "skipped": result.skipped,
    }
    path = migration_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_migration_state() -> dict[str, Any]:
    path = migration_state_path()
    if not path.is_file():
        return {"migrated": [], "verified": [], "skipped": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"migrated": [], "verified": [], "skipped": []}


def migrate_vault_from_env(env_path: Path | None = None, *, only_secret_ref: str | None = None, target_vault: str = "keychain") -> MigrationResult:
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
        if only_secret_ref and secret_ref != only_secret_ref and env_key != only_secret_ref:
            continue
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
        result.verified.append(secret_ref)

    local_path.write_text(json.dumps(local_data, indent=2) + "\n", encoding="utf-8")
    local_path.chmod(0o600)
    if config.vault != "keychain":
        config.vault = "keychain"
    dump_proxy_config(config)
    _write_migration_state(result, target_vault=target_vault)
    return result


def migration_health() -> dict[str, Any]:
    local_path = local_vault_path()
    secrets: dict[str, Any] = {}
    if local_path.is_file():
        try:
            secrets = json.loads(local_path.read_text(encoding="utf-8")).get("secrets", {})
        except json.JSONDecodeError:
            secrets = {}
    config = load_proxy_config()
    migrated_refs = {route.secret_ref for route in config.routes}
    total = len(secrets)
    migrated = sum(1 for ref in secrets if ref in migrated_refs)
    pending = total - migrated
    return {
        "old_vault_path": str(local_path),
        "total": total,
        "migrated": migrated,
        "pending": pending,
        "pending_refs": sorted(ref for ref in secrets if ref not in migrated_refs),
        "status": "migrated" if total and pending == 0 else "pending" if pending else "empty",
    }
