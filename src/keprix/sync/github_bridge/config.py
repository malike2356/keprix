"""Config and scoped storage for GitHub agent-sync."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keprix_constants import get_keprix_home
from keprix.sync.github_bridge.types import (
    DEFAULT_CONFIG,
    DEFAULT_MANIFEST,
    GithubBridgeConfig,
    GithubBridgeManifest,
    GithubBridgeProduct,
    GithubBridgeScopeKind,
)


@dataclass
class GithubBridgeScope:
    scope_kind: GithubBridgeScopeKind = "workspace"
    scope_id: str | None = None
    workspace_id: str | None = None
    user_id: str | None = None


def _normalize_scope_kind(scope_kind: str | None) -> GithubBridgeScopeKind:
    if scope_kind in {"user", "shared", "workspace"}:
        return scope_kind  # type: ignore[return-value]
    return "workspace"


def resolve_github_bridge_scope(scope: GithubBridgeScope | None = None) -> dict[str, Any]:
    scope = scope or GithubBridgeScope()
    scope_kind = _normalize_scope_kind(scope.scope_kind)
    if scope_kind == "user":
        scope_id = (scope.scope_id or scope.user_id or "").strip() or None
    elif scope_kind == "shared":
        scope_id = (scope.scope_id or "shared").strip() or "shared"
    else:
        scope_id = (scope.scope_id or scope.workspace_id or "").strip() or None
    key_id = scope_id or "default"
    return {"scope_kind": scope_kind, "scope_id": scope_id, "scope_key": f"{scope_kind}:{key_id}"}


def data_dir() -> Path:
    return get_keprix_home() / "data"


def scope_data_dir(scope_key: str = "workspace:default") -> Path:
    return data_dir() / "github-agent-sync" / scope_key


def github_bridge_config_path(scope_key: str = "workspace:default") -> Path:
    return scope_data_dir(scope_key) / "config.json"


def github_bridge_token_path(scope_key: str = "workspace:default") -> Path:
    return scope_data_dir(scope_key) / "token"


def github_bridge_index_path(scope_key: str = "workspace:default") -> Path:
    return scope_data_dir(scope_key) / "index.json"


def resolve_clone_path(config: GithubBridgeConfig, scope_key: str = "workspace:default") -> Path:
    if config.local_path and config.local_path.strip():
        return Path(config.local_path.strip()).expanduser().resolve()
    return scope_data_dir(scope_key) / "repo"


def _coerce_product(value: Any) -> GithubBridgeProduct:
    if value in {"keprix", "hermes", "carina", "aiva", "shared"}:
        return value  # type: ignore[return-value]
    return "keprix"


def normalize_config(raw: dict[str, Any] | None = None) -> GithubBridgeConfig:
    base = {**DEFAULT_CONFIG.to_dict(), **(raw or {})}
    # Accept camelCase from Carina-compatible UIs.
    aliases = {
        "scopeKind": "scope_kind",
        "scopeId": "scope_id",
        "pullIntervalMinutes": "pull_interval_minutes",
        "pushIntervalMinutes": "push_interval_minutes",
        "allowedFolders": "allowed_folders",
        "humanEditsWin": "human_edits_win",
        "localPath": "local_path",
        "lastPullAt": "last_pull_at",
        "lastPushAt": "last_push_at",
        "lastIndexAt": "last_index_at",
        "lastError": "last_error",
    }
    for src, dest in aliases.items():
        if src in base and dest not in (raw or {}):
            base[dest] = base[src]
    allowed = base.get("allowed_folders") or DEFAULT_CONFIG.allowed_folders
    return GithubBridgeConfig(
        scope_kind=_normalize_scope_kind(str(base.get("scope_kind") or "workspace")),
        scope_id=(str(base["scope_id"]).strip() or None) if base.get("scope_id") is not None else None,
        enabled=bool(base.get("enabled")),
        owner=str(base.get("owner") or DEFAULT_CONFIG.owner).strip(),
        repo=str(base.get("repo") or DEFAULT_CONFIG.repo).strip(),
        branch=str(base.get("branch") or "main").strip() or "main",
        pull_interval_minutes=max(1, int(base.get("pull_interval_minutes") or 15)),
        push_interval_minutes=max(0, int(base.get("push_interval_minutes") or 0)),
        allowed_folders=[str(item) for item in allowed],
        human_edits_win=base.get("human_edits_win") is not False,
        product=_coerce_product(base.get("product")),
        local_path=(str(base["local_path"]).strip() or None) if base.get("local_path") else None,
        last_pull_at=base.get("last_pull_at"),
        last_push_at=base.get("last_push_at"),
        last_index_at=base.get("last_index_at"),
        last_error=base.get("last_error"),
    )


def _env_enabled() -> bool:
    return os.getenv("AGENT_SYNC_GITHUB_ENABLED", os.getenv("KEPRIX_AGENT_SYNC_GITHUB_ENABLED", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def load_config(scope: GithubBridgeScope | None = None) -> GithubBridgeConfig:
    resolved = resolve_github_bridge_scope(scope)
    path = github_bridge_config_path(resolved["scope_key"])
    if path.is_file():
        raw = json.loads(path.read_text(encoding="utf-8"))
        return normalize_config({**raw, "scope_kind": resolved["scope_kind"], "scope_id": resolved["scope_id"]})
    legacy = data_dir() / "github-agent-sync.json"
    if legacy.is_file():
        raw = json.loads(legacy.read_text(encoding="utf-8"))
        return normalize_config({**raw, "scope_kind": resolved["scope_kind"], "scope_id": resolved["scope_id"]})
    return normalize_config(
        {
            "scope_kind": resolved["scope_kind"],
            "scope_id": resolved["scope_id"],
            "enabled": _env_enabled(),
            "owner": os.getenv("AGENT_SYNC_GITHUB_OWNER") or os.getenv("KEPRIX_AGENT_SYNC_GITHUB_OWNER") or DEFAULT_CONFIG.owner,
            "repo": os.getenv("AGENT_SYNC_GITHUB_REPO") or os.getenv("KEPRIX_AGENT_SYNC_GITHUB_REPO") or DEFAULT_CONFIG.repo,
            "branch": os.getenv("AGENT_SYNC_GITHUB_BRANCH") or os.getenv("KEPRIX_AGENT_SYNC_GITHUB_BRANCH") or DEFAULT_CONFIG.branch,
            "product": os.getenv("AGENT_SYNC_GITHUB_PRODUCT") or os.getenv("KEPRIX_AGENT_SYNC_GITHUB_PRODUCT") or "keprix",
        }
    )


def save_config(patch: dict[str, Any], scope: GithubBridgeScope | None = None) -> GithubBridgeConfig:
    current = load_config(scope)
    next_cfg = normalize_config({**current.to_dict(), **patch})
    resolved = resolve_github_bridge_scope(
        GithubBridgeScope(
            scope_kind=next_cfg.scope_kind,
            scope_id=next_cfg.scope_id,
            workspace_id=scope.workspace_id if scope else None,
            user_id=scope.user_id if scope else None,
        )
    )
    path = github_bridge_config_path(resolved["scope_key"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(next_cfg.to_dict(), indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return next_cfg


def load_token(scope: GithubBridgeScope | None = None) -> str | None:
    resolved = resolve_github_bridge_scope(scope)
    from_env = (
        os.getenv("AGENT_SYNC_GITHUB_TOKEN")
        or os.getenv("KEPRIX_AGENT_SYNC_GITHUB_TOKEN")
        or os.getenv("GITHUB_TOKEN")
        or os.getenv("GH_TOKEN")
        or ""
    ).strip()
    if from_env:
        return from_env
    path = github_bridge_token_path(resolved["scope_key"])
    if not path.is_file():
        return None
    token = path.read_text(encoding="utf-8").strip()
    return token or None


def save_token(token: str | None, scope: GithubBridgeScope | None = None) -> None:
    resolved = resolve_github_bridge_scope(scope)
    path = github_bridge_token_path(resolved["scope_key"])
    path.parent.mkdir(parents=True, exist_ok=True)
    if not token or not token.strip():
        if path.exists():
            path.unlink()
        return
    path.write_text(f"{token.strip()}\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def has_token(scope: GithubBridgeScope | None = None) -> bool:
    return bool(load_token(scope))


def load_manifest(clone_path: Path | None = None) -> GithubBridgeManifest:
    candidates = []
    if clone_path:
        candidates.append(clone_path / "sync" / "manifest.json")
    candidates.append(data_dir() / "agent-sync-manifest.json")
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            raw = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(raw, dict) or not isinstance(raw.get("version"), int):
            continue
        # Support both snake_case and Carina camelCase manifests.
        read_folders = raw.get("read_folders") or raw.get("readFolders") or DEFAULT_MANIFEST.read_folders
        write_folders = raw.get("write_folders") or raw.get("writeFolders") or DEFAULT_MANIFEST.write_folders
        deny_globs = raw.get("deny_globs") or raw.get("denyGlobs") or DEFAULT_MANIFEST.deny_globs
        products_raw = raw.get("products") or {}
        products = {**DEFAULT_MANIFEST.products}
        for key, value in products_raw.items():
            if not isinstance(value, dict):
                continue
            products[key] = {
                "mount_folders": value.get("mount_folders") or value.get("mountFolders") or [],
                "agent_id": value.get("agent_id") or value.get("agentId") or key,
            }
        return GithubBridgeManifest(
            version=int(raw.get("version") or 1),
            canonical_repo=str(raw.get("canonical_repo") or raw.get("canonicalRepo") or DEFAULT_MANIFEST.canonical_repo),
            default_branch=str(raw.get("default_branch") or raw.get("defaultBranch") or "main"),
            read_folders=[str(item) for item in read_folders],
            write_folders=[str(item) for item in write_folders],
            deny_globs=[str(item) for item in deny_globs],
            products=products,
        )
    return DEFAULT_MANIFEST


def write_default_manifest_beside_clone(clone_path: Path) -> Path:
    target = clone_path / "sync" / "manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        # Emit camelCase so Carina/Hermes readers stay compatible.
        payload = {
            "version": DEFAULT_MANIFEST.version,
            "canonicalRepo": DEFAULT_MANIFEST.canonical_repo,
            "defaultBranch": DEFAULT_MANIFEST.default_branch,
            "readFolders": DEFAULT_MANIFEST.read_folders,
            "writeFolders": DEFAULT_MANIFEST.write_folders,
            "denyGlobs": DEFAULT_MANIFEST.deny_globs,
            "products": {
                key: {"mountFolders": value["mount_folders"], "agentId": value["agent_id"]}
                for key, value in DEFAULT_MANIFEST.products.items()
            },
        }
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target
