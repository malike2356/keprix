"""Build production AgentDependencies for typed agent runs."""

from __future__ import annotations

import os
from typing import Any

from keprix.typed_agents.dependencies import AgentDependencies, InMemoryDatabase, SupportDependencies
from keprix.typed_agents.vault_adapter import KeprixVaultAccess


async def build_agent_dependencies(
    *,
    workspace_id: str = "default",
    tenant_id: str | None = None,
    user_id: str = "default",
    permissions: list[str] | None = None,
    feature_flags: dict[str, bool] | None = None,
    include_vault: bool = True,
) -> AgentDependencies:
    """Wire Keprix runtime services into a prompt-safe dependency bundle."""
    flags = dict(feature_flags or {})
    flags.setdefault("governance_enabled", os.environ.get("KEPRIX_GOVERNANCE_ENABLED", "").lower() in {"1", "true", "yes"})
    flags.setdefault("data_workspace", True)

    deps = AgentDependencies(
        workspace_id=workspace_id,
        tenant_id=tenant_id or workspace_id,
        user_id=user_id,
        permissions=permissions or ["agent.read", "agent.run"],
        feature_flags=flags,
    )

    vault = await KeprixVaultAccess.from_user(user_id) if include_vault else None
    return deps.attach_runtime(database=InMemoryDatabase(), vault=vault)


async def build_support_dependencies(
    *,
    workspace_id: str = "default",
    user_id: str = "default",
    permissions: list[str] | None = None,
    feature_flags: dict[str, bool] | None = None,
) -> SupportDependencies:
    base = await build_agent_dependencies(
        workspace_id=workspace_id,
        user_id=user_id,
        permissions=permissions or ["support.read", "support.respond"],
        feature_flags=feature_flags or {"escalation_enabled": True},
    )
    deps = SupportDependencies(
        workspace_id=base.workspace_id,
        tenant_id=base.tenant_id,
        user_id=base.user_id,
        permissions=list(base.permissions),
        feature_flags=dict(base.feature_flags),
        support_tier="standard",
        ticket_queue="general",
    )
    return deps.attach_runtime(
        database=base.database,
        http_client=base.http_client,
        search_client=base.search_client,
        vault=base.vault,
    )


def deps_profile_for_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Resolve optional deps profile hints from an agent app manifest."""
    profile = str(manifest.get("deps_profile") or "default")
    return {"profile": profile, "typed_agent": manifest.get("typed_agent")}
