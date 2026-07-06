"""Interoperability adapter tests."""

from keprix.kernel.interoperability import get_interop_bridge
from keprix.kernel.plugin_contract import get_plugin_registry


def test_mcp_and_a2a_share_plugin_contract() -> None:
    bridge = get_interop_bridge()
    plugin = get_plugin_registry().get("greeting")
    assert plugin is not None
    mcp_tools = bridge.list_mcp_tools()
    a2a_caps = bridge.list_a2a_capabilities()
    assert any(tool["name"] == "greeting.greet" for tool in mcp_tools)
    assert any(agent["agent_id"] == "greeting" for agent in a2a_caps)
    mcp_result = bridge.invoke_mcp_tool("greeting.greet", {"name": "MCP"})
    a2a_result = bridge.invoke_a2a_task(
        {"plugin": "greeting", "function": "greet", "arguments": {"name": "A2A"}}
    )
    assert mcp_result["status"] == "ok"
    assert a2a_result["status"] == "ok"
    sdk_manifest = bridge.to_sdk_manifest(plugin)
    assert sdk_manifest["app_id"] == "greeting"
    assert sdk_manifest["functions"]
