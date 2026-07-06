"""Tests for production typed agent dependency factory."""

from __future__ import annotations

import pytest

from keprix.security.vault_service import reset_vault_service
from keprix.typed_agents.deps_factory import build_agent_dependencies, build_support_dependencies


@pytest.fixture(autouse=True)
def reset_vault() -> None:
    reset_vault_service()


@pytest.mark.asyncio
async def test_build_agent_dependencies_prompt_safe() -> None:
    deps = await build_agent_dependencies(workspace_id="ws-factory", user_id="user-factory")
    safe = deps.prompt_safe_dict()
    dumped = str(safe)
    assert safe["workspace_id"] == "ws-factory"
    assert "secret_value" not in dumped.lower()
    assert safe["has_database"] is True


@pytest.mark.asyncio
async def test_build_support_dependencies_profile() -> None:
    deps = await build_support_dependencies(workspace_id="ws-support", user_id="user-support")
    assert deps.support_tier == "standard"
    assert deps.ticket_queue == "general"
    assert "support.read" in deps.permissions
