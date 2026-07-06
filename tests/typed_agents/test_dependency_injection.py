"""Dependency injection tests for typed agents."""

from __future__ import annotations

import pytest

from keprix.typed_agents.agent import create_support_agent
from keprix.typed_agents.dependencies import VaultAccess, build_support_dependencies
from keprix.typed_agents.schemas import AgentRunContext


@pytest.fixture
def deps():
    return build_support_dependencies(
        workspace_id="ws-di",
        user_id="user-di",
        vault_labels={"smtp": "SMTP credentials", "api": "API key"},
    )


def test_prompt_safe_dict_hides_secret_values(deps) -> None:
    safe = deps.prompt_safe_dict()
    dumped = str(safe)
    assert "API key" in dumped or "SMTP credentials" in dumped
    assert "secret_value" not in dumped
    assert safe["vault"]["secret_labels"] == ["API key", "SMTP credentials"]
    assert safe["has_database"] is True


def test_vault_access_never_returns_raw_secret() -> None:
    vault = VaultAccess("user-1", labels={"item": "Production API token"})
    summary = vault.prompt_safe_summary()
    assert "Production API token" in summary["secret_labels"]
    assert "token_value" not in summary


@pytest.mark.asyncio
async def test_dynamic_instructions_include_safe_context(deps) -> None:
    agent = create_support_agent()
    context = AgentRunContext(workspace_id=deps.workspace_id, user_id=deps.user_id)
    instructions = agent.prepare_instructions(deps, context)
    assert "ws-di" in instructions
    assert "general" in instructions
    assert "secret_value" not in instructions.lower()
