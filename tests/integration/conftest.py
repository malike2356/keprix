"""Shared fixtures for mutation integration tests."""

from __future__ import annotations

import pytest

_TEST_TOOL_NAMES = (
    "send_sms",
    "fetch_weather",
    "demo_tool",
    "manual_tool",
    "low_conf_tool",
)


@pytest.fixture(autouse=True)
def _clean_generated_tools_registry():
    from tools.registry import registry

    for name in _TEST_TOOL_NAMES:
        registry.deregister_tool(name)
    yield
    for name in _TEST_TOOL_NAMES:
        registry.deregister_tool(name)
