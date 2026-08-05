"""GitHub agent-sync durable memory bridge (Carina/Aiva/Hermes-compatible)."""

from keprix.sync.github_bridge.config import (
    GithubBridgeScope,
    load_config,
    resolve_github_bridge_scope,
    save_config,
    save_token,
)
from keprix.sync.github_bridge.scheduler import start_github_bridge_schedule, stop_github_bridge_schedule
from keprix.sync.github_bridge.service import (
    get_status,
    pull_now,
    push_approved_durable_updates,
    rebuild_index,
    run_full_sync_cycle,
    search_shared_knowledge,
    update_settings,
    write_durable_note,
)

__all__ = [
    "GithubBridgeScope",
    "get_status",
    "load_config",
    "pull_now",
    "push_approved_durable_updates",
    "rebuild_index",
    "resolve_github_bridge_scope",
    "run_full_sync_cycle",
    "save_config",
    "save_token",
    "search_shared_knowledge",
    "start_github_bridge_schedule",
    "stop_github_bridge_schedule",
    "update_settings",
    "write_durable_note",
]
