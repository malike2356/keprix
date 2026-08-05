"""Pull/push/index/search service for GitHub agent-sync."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.sync.github_bridge.config import (
    GithubBridgeScope,
    has_token,
    load_config,
    load_manifest,
    load_token,
    resolve_clone_path,
    resolve_github_bridge_scope,
    save_config,
    save_token,
    write_default_manifest_beside_clone,
)
from keprix.sync.github_bridge.git import commit_and_push, ensure_clone, git_diff_names, list_tracked_files, pull_rebase
from keprix.sync.github_bridge.index_store import build_chunk, load_index, save_index, search_index, upsert_rag_chunks
from keprix.sync.github_bridge.policy import is_denied_path, is_under_allowed_folder, normalize_repo_rel_path, should_commit_file
from keprix.sync.github_bridge.types import DEFAULT_MANIFEST, GithubBridgeConfig


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scope_from_config(config: GithubBridgeConfig, scope: GithubBridgeScope | None = None) -> GithubBridgeScope:
    return GithubBridgeScope(
        scope_kind=config.scope_kind,
        scope_id=config.scope_id,
        workspace_id=scope.workspace_id if scope else None,
        user_id=scope.user_id if scope else None,
    )


def _walk_files(root: Path, rel_base: str = "") -> list[str]:
    out: list[str] = []
    base = root / rel_base if rel_base else root
    try:
        entries = list(base.iterdir())
    except OSError:
        return out
    for entry in entries:
        if entry.name in {".git", "node_modules"}:
            continue
        rel = normalize_repo_rel_path(str(Path(rel_base) / entry.name) if rel_base else entry.name)
        if entry.is_dir():
            out.extend(_walk_files(root, rel))
        elif entry.is_file():
            out.append(rel)
    return out


def _read_text_if_small(path: Path, max_bytes: int = 512_000) -> str | None:
    try:
        if not path.is_file() or path.stat().st_size > max_bytes:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def get_status(scope: GithubBridgeScope | None = None) -> dict[str, Any]:
    config = load_config(scope)
    resolved = resolve_github_bridge_scope(_scope_from_config(config, scope))
    local_path = resolve_clone_path(config, resolved["scope_key"])
    index = load_index(GithubBridgeScope(scope_kind=resolved["scope_kind"], scope_id=resolved["scope_id"]))
    return {
        "scope_kind": resolved["scope_kind"],
        "scope_id": resolved["scope_id"],
        "scope_key": resolved["scope_key"],
        "configured": bool(config.owner and config.repo),
        "enabled": config.enabled,
        "has_token": has_token(GithubBridgeScope(scope_kind=resolved["scope_kind"], scope_id=resolved["scope_id"])),
        "repo": f"{config.owner}/{config.repo}" if config.owner and config.repo else None,
        "branch": config.branch,
        "local_path": str(local_path),
        "clone_exists": (local_path / ".git").exists(),
        "allowed_folders": config.allowed_folders,
        "pull_interval_minutes": config.pull_interval_minutes,
        "push_interval_minutes": config.push_interval_minutes,
        "human_edits_win": config.human_edits_win,
        "product": config.product,
        "last_pull_at": config.last_pull_at,
        "last_push_at": config.last_push_at,
        "last_index_at": config.last_index_at,
        "last_error": config.last_error,
        "indexed_chunks": len(index.get("chunks") or []),
        # camelCase aliases for Carina-compatible clients
        "scopeKind": resolved["scope_kind"],
        "scopeId": resolved["scope_id"],
        "scopeKey": resolved["scope_key"],
        "hasToken": has_token(GithubBridgeScope(scope_kind=resolved["scope_kind"], scope_id=resolved["scope_id"])),
        "localPath": str(local_path),
        "cloneExists": (local_path / ".git").exists(),
        "allowedFolders": config.allowed_folders,
        "pullIntervalMinutes": config.pull_interval_minutes,
        "pushIntervalMinutes": config.push_interval_minutes,
        "humanEditsWin": config.human_edits_win,
        "lastPullAt": config.last_pull_at,
        "lastPushAt": config.last_push_at,
        "lastIndexAt": config.last_index_at,
        "lastError": config.last_error,
        "indexedChunks": len(index.get("chunks") or []),
    }


def update_settings(input_data: dict[str, Any], scope: GithubBridgeScope | None = None) -> dict[str, Any]:
    resolved = resolve_github_bridge_scope(
        GithubBridgeScope(
            scope_kind=input_data.get("scope_kind") or input_data.get("scopeKind") or (scope.scope_kind if scope else "workspace"),
            scope_id=input_data.get("scope_id") if "scope_id" in input_data else input_data.get("scopeId", scope.scope_id if scope else None),
            workspace_id=scope.workspace_id if scope else None,
            user_id=scope.user_id if scope else None,
        )
    )
    scoped = GithubBridgeScope(scope_kind=resolved["scope_kind"], scope_id=resolved["scope_id"])
    if "token" in input_data:
        save_token(input_data.get("token"), scoped)
    patch = {
        key: value
        for key, value in {
            "scope_kind": resolved["scope_kind"],
            "scope_id": resolved["scope_id"],
            "enabled": input_data.get("enabled"),
            "owner": input_data.get("owner"),
            "repo": input_data.get("repo"),
            "branch": input_data.get("branch"),
            "pull_interval_minutes": input_data.get("pull_interval_minutes", input_data.get("pullIntervalMinutes")),
            "push_interval_minutes": input_data.get("push_interval_minutes", input_data.get("pushIntervalMinutes")),
            "allowed_folders": input_data.get("allowed_folders", input_data.get("allowedFolders")),
            "human_edits_win": input_data.get("human_edits_win", input_data.get("humanEditsWin")),
            "product": input_data.get("product"),
            "local_path": input_data.get("local_path", input_data.get("localPath")),
        }.items()
        if value is not None
    }
    save_config(patch, scoped)
    return get_status(scoped)


def rebuild_index(config: GithubBridgeConfig | None = None, scope: GithubBridgeScope | None = None) -> int:
    cfg = config or load_config(scope)
    scoped = _scope_from_config(cfg, scope)
    resolved = resolve_github_bridge_scope(scoped)
    local_path = resolve_clone_path(cfg, resolved["scope_key"])
    manifest = load_manifest(local_path)
    product_mount = manifest.products.get(cfg.product) or DEFAULT_MANIFEST.products["keprix"]
    folders = cfg.allowed_folders or product_mount.get("mount_folders") or []
    chunks = []
    for rel in _walk_files(local_path):
        if is_denied_path(rel, manifest):
            continue
        if not is_under_allowed_folder(rel, folders):
            continue
        content = _read_text_if_small(local_path / rel)
        if content is None:
            continue
        chunks.append(
            build_chunk(
                path=rel,
                content=content,
                product=cfg.product,
                agent=str(product_mount.get("agent_id") or cfg.product),
            )
        )
    save_index(chunks, scoped)
    upsert_rag_chunks(chunks, scoped)
    save_config({"last_index_at": _now(), "last_error": None}, scoped)
    return len(chunks)


def pull_now(scope: GithubBridgeScope | None = None) -> dict[str, Any]:
    config = load_config(scope)
    scoped = _scope_from_config(config, scope)
    resolved = resolve_github_bridge_scope(scoped)
    token = load_token(scoped)
    if not config.enabled:
        return {"ok": False, "action": "pull", "error": "GitHub agent sync is disabled"}
    if not token:
        return {"ok": False, "action": "pull", "error": "Missing AGENT_SYNC_GITHUB_TOKEN / GITHUB_TOKEN"}
    local_path = resolve_clone_path(config, resolved["scope_key"])
    try:
        ensure_clone(owner=config.owner, repo=config.repo, branch=config.branch, token=token, local_path=local_path)
        preserved: dict[str, str] = {}
        if config.human_edits_win:
            for rel in git_diff_names(local_path):
                if not is_under_allowed_folder(rel, config.allowed_folders):
                    continue
                content = _read_text_if_small(local_path / rel)
                if content is not None:
                    preserved[rel] = content
        pull_rebase(local_path=local_path, branch=config.branch, token=token, owner=config.owner, repo=config.repo)
        skipped_human: list[str] = []
        for rel, content in preserved.items():
            abs_path = local_path / rel
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")
            skipped_human.append(rel)
        write_default_manifest_beside_clone(local_path)
        indexed = rebuild_index(config, scoped)
        save_config({"last_pull_at": _now(), "last_error": None}, scoped)
        return {"ok": True, "action": "pull", "pulled": True, "indexed": indexed, "skipped_human": skipped_human, "skippedHuman": skipped_human}
    except Exception as exc:
        error = str(exc)
        save_config({"last_error": error}, scoped)
        return {"ok": False, "action": "pull", "error": error}


def push_approved_durable_updates(
    opts: dict[str, Any] | None = None,
    scope: GithubBridgeScope | None = None,
) -> dict[str, Any]:
    opts = opts or {}
    config = load_config(scope)
    scoped = _scope_from_config(config, scope)
    resolved = resolve_github_bridge_scope(scoped)
    token = load_token(scoped)
    if not config.enabled:
        return {"ok": False, "action": "push", "error": "GitHub agent sync is disabled"}
    if not token:
        return {"ok": False, "action": "push", "error": "Missing AGENT_SYNC_GITHUB_TOKEN / GITHUB_TOKEN"}
    local_path = resolve_clone_path(config, resolved["scope_key"])
    if not (local_path / ".git").exists():
        return {"ok": False, "action": "push", "error": "Clone missing; pull first"}
    manifest = load_manifest(local_path)
    candidates = [normalize_repo_rel_path(p) for p in (opts.get("paths") or [])] or (
        list_tracked_files(local_path) if (local_path / ".git").exists() else _walk_files(local_path)
    )
    committed_files: list[str] = []
    skipped_secrets: list[str] = []
    for rel in candidates:
        content = _read_text_if_small(local_path / rel)
        if content is None:
            continue
        ok, reason = should_commit_file(rel_path=rel, content=content, allowed_write_folders=manifest.write_folders, manifest=manifest)
        if not ok:
            if reason and "secret" in reason:
                skipped_secrets.append(rel)
            continue
        committed_files.append(rel)
    if not committed_files:
        return {"ok": True, "action": "push", "pushed": False, "committed_files": [], "committedFiles": [], "skipped_secrets": skipped_secrets, "skippedSecrets": skipped_secrets}
    try:
        pull_rebase(local_path=local_path, branch=config.branch, token=token, owner=config.owner, repo=config.repo)
        agent_id = (manifest.products.get(config.product) or DEFAULT_MANIFEST.products["keprix"]).get("agent_id") or config.product
        result = commit_and_push(
            local_path=local_path,
            branch=config.branch,
            token=token,
            owner=config.owner,
            repo=config.repo,
            message=(opts.get("message") or "").strip() or f"agent({agent_id}): durable memory sync",
            paths=committed_files,
        )
        save_config({"last_push_at": _now() if result["pushed"] else config.last_push_at, "last_error": None}, scoped)
        return {
            "ok": True,
            "action": "push",
            "pushed": result["pushed"],
            "committed_files": committed_files if result["committed"] else [],
            "committedFiles": committed_files if result["committed"] else [],
            "skipped_secrets": skipped_secrets,
            "skippedSecrets": skipped_secrets,
        }
    except Exception as exc:
        error = str(exc)
        save_config({"last_error": error}, scoped)
        return {"ok": False, "action": "push", "error": error, "skipped_secrets": skipped_secrets, "committed_files": committed_files}


def write_durable_note(
    *,
    relative_path: str,
    content: str,
    push: bool = True,
    scope: GithubBridgeScope | None = None,
) -> dict[str, Any]:
    config = load_config(scope)
    scoped = _scope_from_config(config, scope)
    resolved = resolve_github_bridge_scope(scoped)
    local_path = resolve_clone_path(config, resolved["scope_key"])
    manifest = load_manifest(local_path)
    rel = normalize_repo_rel_path(relative_path)
    ok, reason = should_commit_file(rel_path=rel, content=content, allowed_write_folders=manifest.write_folders, manifest=manifest)
    if not ok:
        return {"ok": False, "action": "push", "error": reason}
    abs_path = local_path / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
    if not push:
        return {"ok": True, "action": "push", "pushed": False, "committed_files": [rel], "committedFiles": [rel]}
    return push_approved_durable_updates({"paths": [rel]}, scoped)


def search_shared_knowledge(
    query: str,
    limit: int = 8,
    filters: dict[str, str] | None = None,
    scope: GithubBridgeScope | None = None,
) -> list[dict[str, Any]]:
    index = load_index(scope)
    if not index.get("chunks"):
        status = get_status(scope)
        if status.get("clone_exists"):
            rebuild_index(scope=scope)
            index = load_index(scope)
    return search_index(index, query, limit, filters)


def run_full_sync_cycle(scope: GithubBridgeScope | None = None) -> dict[str, Any]:
    pull = pull_now(scope)
    if not pull.get("ok"):
        return {**pull, "action": "full"}
    config = load_config(scope)
    scoped = _scope_from_config(config, scope)
    if config.push_interval_minutes > 0:
        push = push_approved_durable_updates({}, scoped)
        return {
            "ok": push.get("ok"),
            "action": "full",
            "pulled": True,
            "pushed": push.get("pushed"),
            "indexed": pull.get("indexed"),
            "committed_files": push.get("committed_files"),
            "skipped_secrets": push.get("skipped_secrets"),
            "error": push.get("error"),
        }
    return {"ok": True, "action": "full", "pulled": True, "indexed": pull.get("indexed"), "pushed": False}
