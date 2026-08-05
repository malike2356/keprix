"""Receive and apply Governance policies."""

from __future__ import annotations

from typing import Any

from keprix.governance.kill_relay import apply_kill_directive
from keprix.governance.store import get_governance_store


class PolicyRegistry:
    def __init__(self) -> None:
        self._rate_limit_per_minute: int | None = None
        self._blocked_tools: set[str] = set()
        self._allowed_providers: set[str] | None = None
        self._feature_flags: dict[str, bool] = {}

    def apply(self, policy_type: str, policy_value: dict[str, Any]) -> None:
        if policy_type == "rate_limit":
            self._rate_limit_per_minute = int(policy_value.get("calls_per_minute") or policy_value.get("limit") or 0)
        elif policy_type == "tool_block":
            tool_name = str(policy_value.get("tool_name") or policy_value.get("name") or "").strip()
            if tool_name:
                self._blocked_tools.add(tool_name)
        elif policy_type == "provider_restrict":
            providers = policy_value.get("providers") or policy_value.get("allowed") or []
            self._allowed_providers = {str(name).strip() for name in providers if str(name).strip()}
        elif policy_type == "feature_flag":
            name = str(policy_value.get("name") or policy_value.get("feature") or "").strip()
            if name:
                self._feature_flags[name] = bool(policy_value.get("enabled", True))
        elif policy_type in {"stop_agent", "lock_workspace", "disable_tools"}:
            apply_kill_directive(policy_type, policy_value)

    def reload_from_store(self, policies: list[dict[str, Any]]) -> None:
        self._rate_limit_per_minute = None
        self._blocked_tools = set()
        self._allowed_providers = None
        self._feature_flags = {}
        for row in policies:
            if not row.get("active", True):
                continue
            self.apply(str(row["policy_type"]), dict(row.get("policy_value") or {}))

    def is_tool_blocked(self, tool_name: str) -> bool:
        return tool_name in self._blocked_tools

    def provider_allowed(self, provider: str) -> bool:
        if self._allowed_providers is None:
            return True
        return provider in self._allowed_providers

    def feature_enabled(self, feature: str, *, default: bool = True) -> bool:
        if feature not in self._feature_flags:
            return default
        return self._feature_flags[feature]

    def rate_limit_per_minute(self) -> int | None:
        return self._rate_limit_per_minute

    def clear_rate_limit(self) -> None:
        self._rate_limit_per_minute = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "rate_limit_per_minute": self._rate_limit_per_minute,
            "blocked_tools": sorted(self._blocked_tools),
            "allowed_providers": sorted(self._allowed_providers) if self._allowed_providers else None,
            "feature_flags": dict(self._feature_flags),
        }


_registry = PolicyRegistry()


def get_policy_registry() -> PolicyRegistry:
    return _registry


async def apply_policy(policy_type: str, policy_value: dict[str, Any]) -> dict[str, Any]:
    store = get_governance_store()
    row = await store.add_policy(policy_type, policy_value)
    _registry.apply(policy_type, policy_value)
    return row


async def reload_policies() -> None:
    store = get_governance_store()
    policies = await store.list_policies(active_only=True)
    _registry.reload_from_store(policies)
