"""Plugin contract tests."""

from keprix.kernel.function_contract import get_invocation_traces
from keprix.kernel.plugin_contract import get_plugin_registry


def test_plugin_can_be_inspected_and_invoked() -> None:
    registry = get_plugin_registry()
    plugin = registry.inspect("greeting")
    assert plugin is not None
    assert plugin["name"] == "greeting"
    result = registry.invoke("greeting", "greet", {"name": "Ada"})
    assert result["status"] == "ok"
    assert result["output"]["message"] == "Hello, Ada"
    traces = get_invocation_traces()
    assert traces
    assert traces[-1]["function_name"] == "greet"
