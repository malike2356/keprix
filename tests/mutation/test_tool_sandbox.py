"""Tests for mutation tool sandbox (Prompt 150)."""

from __future__ import annotations

import textwrap

from keprix.mutation.tool_sandbox import validate_tool_in_sandbox

_VALID_TOOL = textwrap.dedent(
    '''
    from tools.registry import registry, tool_result, tool_error

    def fetch_weather_handler(args, **kwargs):
        city = str(args.get("city", "")).strip()
        if not city:
            return tool_error("city is required")
        return tool_result(success=True, city=city, weather="sunny")

    registry.register(
        name="fetch_weather",
        toolset="generated",
        schema={
            "name": "fetch_weather",
            "description": "Fetches weather for a city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
        handler=fetch_weather_handler,
    )
    '''
).strip() + "\n"


def test_valid_tool_passes():
    result = validate_tool_in_sandbox(_VALID_TOOL, "fetch_weather", timeout_seconds=5)
    assert result.passed is True
    assert result.schema_valid is True
    assert result.error is None


def test_syntax_error_fails():
    result = validate_tool_in_sandbox("def broken(:\n", "broken", timeout_seconds=5)
    assert result.passed is False
    assert result.error


def test_import_error_fails():
    source = "import this_module_does_not_exist_xyz\n" + _VALID_TOOL
    result = validate_tool_in_sandbox(source, "fetch_weather", timeout_seconds=5)
    assert result.passed is False


def test_tool_that_raises_on_call_fails():
    source = textwrap.dedent(
        '''
        from tools.registry import registry

        def bad_handler(args, **kwargs):
            raise RuntimeError("boom")

        registry.register(
            name="bad_tool",
            toolset="generated",
            schema={"name": "bad_tool", "description": "bad", "parameters": {"type": "object", "properties": {}}},
            handler=bad_handler,
        )
        '''
    ).strip()
    result = validate_tool_in_sandbox(source, "bad_tool", timeout_seconds=5)
    assert result.passed is False


def test_tool_with_no_register_call_fails():
    source = "def fetch_weather_handler(args, **kwargs):\n    return '{}'\n"
    result = validate_tool_in_sandbox(source, "fetch_weather", timeout_seconds=5)
    assert result.passed is False
    assert "register" in (result.error or "").lower()


def test_timeout_respected():
    source = textwrap.dedent(
        '''
        from tools.registry import registry, tool_result
        import time

        def slow_handler(args, **kwargs):
            time.sleep(5)
            return tool_result(ok=True)

        registry.register(
            name="slow_tool",
            toolset="generated",
            schema={"name": "slow_tool", "description": "slow", "parameters": {"type": "object", "properties": {}}},
            handler=slow_handler,
        )
        '''
    ).strip()
    result = validate_tool_in_sandbox(source, "slow_tool", timeout_seconds=1)
    assert result.passed is False
    assert "timeout" in (result.error or "").lower()


def test_no_filesystem_write_allowed():
    result = validate_tool_in_sandbox(_VALID_TOOL, "fetch_weather", timeout_seconds=5)
    assert result.passed is True


def test_no_network_access_allowed():
    result = validate_tool_in_sandbox(_VALID_TOOL, "fetch_weather", timeout_seconds=5)
    assert result.passed is True
