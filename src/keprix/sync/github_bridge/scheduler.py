"""Background pull/push scheduler for GitHub agent-sync."""

from __future__ import annotations

import logging
import os
import threading
from typing import Any

from keprix.sync.github_bridge.config import GithubBridgeScope, data_dir, load_config, resolve_github_bridge_scope
from keprix.sync.github_bridge.service import pull_now, push_approved_durable_updates

log = logging.getLogger(__name__)

_timers: dict[str, dict[str, threading.Timer | None]] = {}
_lock = threading.Lock()


def github_bridge_scheduler_enabled() -> bool:
    if os.getenv("AGENT_SYNC_GITHUB_ENABLED", "").strip().lower() in {"0", "false", "no", "off"}:
        return False
    if os.getenv("KEPRIX_AGENT_SYNC_GITHUB_ENABLED", "").strip().lower() in {"0", "false", "no", "off"}:
        return False
    return True


def _stop_scope_timers(scope_key: str) -> None:
    with _lock:
        timers = _timers.pop(scope_key, None)
    if not timers:
        return
    for timer in timers.values():
        if timer is not None:
            timer.cancel()


def stop_github_bridge_schedule() -> None:
    with _lock:
        keys = list(_timers.keys())
    for key in keys:
        _stop_scope_timers(key)


def _list_scheduled_configs() -> list[dict[str, Any]]:
    base = data_dir() / "github-agent-sync"
    scoped: list[dict[str, Any]] = []
    if base.is_dir():
        for entry in base.iterdir():
            if not entry.is_dir() or ":" not in entry.name:
                continue
            kind, _, rest = entry.name.partition(":")
            scope_kind = kind if kind in {"user", "shared", "workspace"} else "workspace"
            scope = GithubBridgeScope(scope_kind=scope_kind, scope_id=rest or None)  # type: ignore[arg-type]
            config = load_config(scope)
            if config.enabled:
                resolved = resolve_github_bridge_scope(scope)
                scoped.append({"scope_key": resolved["scope_key"], "config": config, "scope": scope})
    if scoped:
        return scoped
    default = load_config()
    if not default.enabled:
        return []
    resolved = resolve_github_bridge_scope(GithubBridgeScope(scope_kind=default.scope_kind, scope_id=default.scope_id))
    return [{"scope_key": resolved["scope_key"], "config": default, "scope": GithubBridgeScope(scope_kind=default.scope_kind, scope_id=default.scope_id)}]


def _schedule_repeating(scope_key: str, kind: str, interval_s: float, fn) -> None:
    def _tick() -> None:
        try:
            fn()
        except Exception as exc:
            log.warning("[agent-sync:%s] %s failed: %s", scope_key, kind, exc)
        timer = threading.Timer(interval_s, _tick)
        timer.daemon = True
        timer.start()
        with _lock:
            bucket = _timers.setdefault(scope_key, {"pull": None, "push": None})
            bucket[kind] = timer

    first = threading.Timer(0.1, _tick)
    first.daemon = True
    first.start()
    with _lock:
        bucket = _timers.setdefault(scope_key, {"pull": None, "push": None})
        bucket[kind] = first


def _schedule_scope(scope_key: str, config, scope: GithubBridgeScope) -> None:
    _stop_scope_timers(scope_key)

    def _pull() -> None:
        result = pull_now(scope)
        if not result.get("ok") and result.get("error"):
            log.warning("[agent-sync:%s] pull: %s", scope_key, result["error"])

    pull_s = max(config.pull_interval_minutes, 1) * 60
    _schedule_repeating(scope_key, "pull", float(pull_s), _pull)
    if config.push_interval_minutes > 0:
        push_s = max(config.push_interval_minutes, 1) * 60

        def _push() -> None:
            result = push_approved_durable_updates({}, scope)
            if not result.get("ok") and result.get("error"):
                log.warning("[agent-sync:%s] push: %s", scope_key, result["error"])

        _schedule_repeating(scope_key, "push", float(push_s), _push)
    log.info(
        "[agent-sync:%s] scheduled (pull every %sm%s) -> %s/%s@%s",
        scope_key,
        config.pull_interval_minutes,
        f", push every {config.push_interval_minutes}m" if config.push_interval_minutes > 0 else ", push on save only",
        config.owner,
        config.repo,
        config.branch,
    )


def start_github_bridge_schedule() -> None:
    if not github_bridge_scheduler_enabled():
        return
    stop_github_bridge_schedule()
    configs = _list_scheduled_configs()
    if not configs:
        log.info("[agent-sync] GitHub bridge idle (disabled). Enable in Settings or AGENT_SYNC_GITHUB_ENABLED=true")
        return
    for item in configs:
        _schedule_scope(item["scope_key"], item["config"], item["scope"])
