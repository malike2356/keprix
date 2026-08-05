"""Credential rotation detection, state, and signal helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from keprix.proxy.cache import CredentialCache, parse_duration_seconds
from keprix.proxy.config import ProxyConfig, RouteConfig
from keprix.proxy.paths import rotation_signal_path, rotation_state_path
from keprix.proxy.secret import Secret
from keprix.proxy.vault import VaultProvider, get_vault_provider
from keprix.tools.credential_audit import record_credential_audit


def hash_secret(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> dict[str, Any]:
    path = rotation_state_path()
    if not path.is_file():
        return {"credentials": {}, "events": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"credentials": {}, "events": []}


def _save_state(state: dict[str, Any]) -> None:
    path = rotation_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def record_rotation_event(secret_ref: str, *, previous_hash: str | None, new_hash: str, trigger: str, status: str = "healthy") -> dict[str, Any]:
    event = {
        "event": "credential.rotated",
        "secret_ref": secret_ref,
        "previous_hash": previous_hash,
        "new_hash": new_hash,
        "timestamp": _now(),
        "trigger": trigger,
        "status": status,
    }
    state = _load_state()
    state.setdefault("events", []).append(event)
    state.setdefault("credentials", {})[secret_ref] = {
        "secret_ref": secret_ref,
        "last_rotated": event["timestamp"],
        "last_hash": new_hash,
        "status": status,
    }
    _save_state(state)
    record_credential_audit(
        tool="credential_proxy",
        route={"host": "", "path": "rotation", "method": "ROTATE"},
        credential_ref=secret_ref,
        status="rotated" if status == "healthy" else status,
    )
    return event


def write_rotation_signal(secret_ref: str, *, verify: bool = False) -> dict[str, Any]:
    payload = {"secret_ref": secret_ref, "verify": verify, "timestamp": _now()}
    path = rotation_signal_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def consume_rotation_signal() -> dict[str, Any] | None:
    path = rotation_signal_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        payload = None
    path.unlink(missing_ok=True)
    return payload if isinstance(payload, dict) else None


def _route_ttl(route: RouteConfig) -> float:
    if not route.cache or route.cache == "none":
        return 0.0
    if isinstance(route.cache, dict):
        return parse_duration_seconds(route.cache.get("ttl"))
    return parse_duration_seconds(str(route.cache))


def _probe(secret: Secret) -> bool:
    value = secret.expose()
    return bool(value.strip()) and not value.startswith("bad")


class CredentialRotationManager:
    def __init__(self, config: ProxyConfig, vault: VaultProvider | None = None, cache: CredentialCache | None = None) -> None:
        self.config = config
        self.vault = vault or get_vault_provider(config.vault)
        self.cache = cache or CredentialCache()
        self._hashes: dict[str, str] = {}
        self._last_good: dict[str, Secret] = {}

    def fetch_for_route(self, route: RouteConfig) -> Secret:
        signal = consume_rotation_signal()
        if signal and signal.get("secret_ref") in {route.secret_ref, "*"}:
            self.cache.invalidate(route.secret_ref)
        ttl = _route_ttl(route)

        def _fetch() -> tuple[Secret, str]:
            secret = self.vault.fetch(route.secret_ref)
            digest = hash_secret(secret.expose())
            return secret, digest

        secret, digest, from_cache = self.cache.get(route.secret_ref, ttl_seconds=ttl, fetch=_fetch)
        previous = self._hashes.get(route.secret_ref)
        if previous and previous != digest and not from_cache:
            if signal and signal.get("verify") and not _probe(secret):
                old = self._last_good.get(route.secret_ref)
                record_rotation_event(route.secret_ref, previous_hash=previous, new_hash=digest, trigger="manual_verify", status="failed")
                if old:
                    secret.clear()
                    return Secret(old.expose())
            else:
                record_rotation_event(route.secret_ref, previous_hash=previous, new_hash=digest, trigger="cache_expiry" if not signal else "manual")
        self._hashes[route.secret_ref] = digest
        old = self._last_good.get(route.secret_ref)
        if old:
            old.clear()
        self._last_good[route.secret_ref] = Secret(secret.expose())
        return secret

    def invalidate(self, secret_ref: str | None = None) -> int:
        return self.cache.invalidate(secret_ref)


def rotation_status(config: ProxyConfig) -> dict[str, Any]:
    state = _load_state()
    credentials = state.get("credentials", {})
    rows = []
    for route in config.routes:
        current = credentials.get(route.secret_ref, {})
        ttl = "none"
        if isinstance(route.cache, dict):
            ttl = str(route.cache.get("ttl") or "none")
        elif route.cache:
            ttl = str(route.cache)
        rows.append(
            {
                "secret_ref": route.secret_ref,
                "host": route.host,
                "last_rotated": current.get("last_rotated"),
                "cache_ttl": ttl,
                "rotation": route.rotation,
                "status": current.get("status") or "unknown",
            }
        )
    return {"credentials": rows, "events": list(reversed(state.get("events", [])))[:100]}
