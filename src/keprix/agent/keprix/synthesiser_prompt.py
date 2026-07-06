"""Prompt templates and examples for mutation tool synthesis."""

from __future__ import annotations

EXAMPLE_TOOL_ECHO = '''
"""Example: echo_text generated tool."""
from tools.registry import registry, tool_error, tool_result

def echo_text_handler(args, **kwargs):
    text = str(args.get("text", "")).strip()
    if not text:
        return tool_error("text is required")
    return tool_result(success=True, echo=text)

registry.register(
    name="echo_text",
    toolset="generated",
    schema={
        "name": "echo_text",
        "description": "Echo text back to the caller.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to echo"},
            },
            "required": ["text"],
        },
    },
    handler=echo_text_handler,
    emoji="🧬",
)
'''.strip()

EXAMPLE_TOOL_STOCK = '''
"""Example: fetch_stock_price generated tool (offline sandbox friendly)."""
from tools.registry import registry, tool_error, tool_result

_MOCK_PRICES = {
    "AAPL": 213.42,
    "MSFT": 420.10,
    "GOOG": 175.25,
}

def fetch_stock_price_handler(args, **kwargs):
    ticker = str(args.get("ticker", "")).upper().strip()
    if not ticker:
        return tool_error("ticker is required")
    price = _MOCK_PRICES.get(ticker)
    if price is None:
        return tool_error(f"No price available for {ticker}")
    return tool_result(success=True, ticker=ticker, price=price, currency="USD")

registry.register(
    name="fetch_stock_price",
    toolset="generated",
    schema={
        "name": "fetch_stock_price",
        "description": "Fetch a stock price for a ticker symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["ticker"],
        },
    },
    handler=fetch_stock_price_handler,
    emoji="🧬",
)
'''.strip()

SYSTEM_PROMPT = """You synthesize safe Python tools for the Keprix mutation engine.

Return ONLY a JSON object with these keys:
- tool_code: complete Python module as a string
- skill_yaml: companion YAML skill file as a string
- test_input: dict of arguments for sandbox smoke test

Tool code requirements:
1. Register with tools.registry using registry.register(...) at module top level.
2. Import only from: tools.registry (registry, tool_result, tool_error), stdlib, httpx, json, re, datetime, math, typing.
3. Handler signature: def <tool_name>_handler(args, **kwargs) -> str
4. Handler must return tool_result(...) or tool_error(...) JSON strings.
5. NEVER import keprix, agent, backend, subprocess, socket, ctypes, pickle, eval, exec, __import__.
6. Sandbox runs with NO network. Handler MUST succeed offline for test_input using deterministic mock data or pure logic.
7. Use the exact tool name provided in registry.register(name=...).
8. schema.description must match the gap. parameters must reflect test_input keys.

skill_yaml requirements:
- name, description, triggers (3-5 strings), tools list with the tool name.

Output valid JSON only. No markdown fences."""


def build_user_prompt(
    *,
    tool_name: str,
    description: str,
    task: str,
    approach: str,
    rewrite_hint: str | None,
) -> str:
    rewrite = f"\nRewrite after static analysis failure:\n{rewrite_hint}\n" if rewrite_hint else ""
    return (
        f"Synthesize a tool for this capability gap.\n"
        f"Task: {task}\n"
        f"Gap: {description}\n"
        f"Suggested approach: {approach or 'Implement the smallest safe tool that closes the gap.'}\n"
        f"Required tool name: {tool_name}\n"
        f"{rewrite}\n"
        "Examples of valid generated tools:\n"
        f"--- example 1 ---\n{EXAMPLE_TOOL_ECHO}\n"
        f"--- example 2 ---\n{EXAMPLE_TOOL_STOCK}\n"
        "Generate tool_code, skill_yaml, and test_input for the gap above."
    )
