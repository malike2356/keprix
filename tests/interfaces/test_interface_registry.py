"""Tests for agent interface registry."""

from __future__ import annotations

import pytest

from keprix.interfaces.interface_registry import InterfaceKind, InterfaceRegistry, get_interface_registry


@pytest.fixture
def registry() -> InterfaceRegistry:
    reg = InterfaceRegistry()
    from keprix.interfaces.ag_ui_adapter import handle_ag_ui
    from keprix.interfaces.a2a_interface import handle_a2a
    from keprix.interfaces.interface_registry import _api_handler
    from keprix.interfaces.web_ui_stream import _web_ui_handler
    from keprix.interfaces.telegram_interface import handle_telegram

    reg.register_handler(InterfaceKind.WEB_UI, _web_ui_handler)
    reg.register_handler(InterfaceKind.API, _api_handler)
    reg.register_handler(InterfaceKind.TELEGRAM, handle_telegram)
    reg.register_handler(InterfaceKind.A2A, handle_a2a)
    reg.register_handler(InterfaceKind.AG_UI, handle_ag_ui)
    reg.bind_agent("demo-agent", [InterfaceKind.WEB_UI, InterfaceKind.TELEGRAM, InterfaceKind.AG_UI])
    return reg


@pytest.mark.asyncio
async def test_agent_exposed_via_web_ui_and_telegram(registry: InterfaceRegistry) -> None:
    web = await registry.dispatch("demo-agent", InterfaceKind.WEB_UI, message="/status", user_id="tester")
    assert web.ok
    assert web.trace_id

    telegram = await registry.dispatch(
        "demo-agent",
        InterfaceKind.TELEGRAM,
        text="/status",
        user_id="tester",
        chat_id="123",
        trace_id=web.trace_id,
    )
    assert telegram.ok
    assert telegram.payload.get("interface") == "telegram"
    assert telegram.trace_id == web.trace_id


@pytest.mark.asyncio
async def test_disabled_interface_blocked(registry: InterfaceRegistry) -> None:
    registry.bind_agent("locked-agent", [InterfaceKind.API])
    result = await registry.dispatch("locked-agent", InterfaceKind.TELEGRAM, text="/status")
    assert not result.ok
    assert "not enabled" in (result.error or "")


def test_global_registry_singleton() -> None:
    assert get_interface_registry() is get_interface_registry()
