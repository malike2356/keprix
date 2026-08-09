from __future__ import annotations

import pytest

from keprix.product_sidecar.handlers import handle_agent_run
from keprix.product_sidecar.types import RequestContext


def _context(product: str) -> RequestContext:
    return RequestContext(
        product=product,
        deployment="test",
        workspace_id="ws-routing",
        actor_id="actor",
        grants=frozenset(),
        purpose="test",
        correlation_id="corr",
    )


@pytest.mark.asyncio
async def test_aiva_agent_run_uses_fast_route(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, object] = {}

    async def fake_run(_self, **kwargs):
        observed.update(kwargs)
        return {"message": {"role": "assistant", "content": "ok"}}

    monkeypatch.setenv("AIVA_PROVIDER", "openai")
    monkeypatch.setenv("AIVA_MODEL", "gpt-4o-mini")
    monkeypatch.setattr("keprix.agent.carina_bridge.CarinaAgentBridge.run", fake_run)

    result = await handle_agent_run(
        _context("aiva"),
        {"messages": [{"role": "user", "content": "hello"}], "system_prompt": "help"},
    )

    assert observed["model"] == "openai:gpt-4o-mini"
    assert result["model_routing"]["tier"] == "starter"


@pytest.mark.asyncio
async def test_carina_engineering_model_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, object] = {}

    async def fake_run(_self, **kwargs):
        observed.update(kwargs)
        return {"message": {"role": "assistant", "content": "ok"}}

    monkeypatch.setattr("keprix.agent.carina_bridge.CarinaAgentBridge.run", fake_run)
    result = await handle_agent_run(
        _context("carina"),
        {
            "model": "deepseek-v4-pro",
            "messages": [{"role": "user", "content": "build"}],
            "system_prompt": "engineer",
        },
    )

    assert observed["model"] == "deepseek-v4-pro"
    assert "model_routing" not in result
