"""Tests for post-approval task retry (Prompt 141)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from keprix.agent.keprix.retry import KeprixRetry, _extract_track_time_project


@pytest.fixture
def retry() -> KeprixRetry:
    return KeprixRetry()


def test_extract_track_time_project_from_on_phrase():
    assert _extract_track_time_project("Track my time on this project") == "this project"


@pytest.mark.asyncio
async def test_retry_fetch_stock_price_formats_price(retry, monkeypatch):
    registry = SimpleNamespace(
        get_entry=lambda name: SimpleNamespace(schema={"parameters": {"required": ["ticker"]}}) if name == "fetch_stock_price" else None,
        dispatch=lambda name, args, **kwargs: json.dumps({"success": True, "ticker": args["ticker"], "price": 213.42}),
    )
    monkeypatch.setitem(__import__("sys").modules, "tools.registry", SimpleNamespace(registry=registry))

    message = await retry.retry(
        original_message="fetch AAPL stock price",
        tool_name="fetch_stock_price",
    )
    assert "213.42" in message
    assert "AAPL" in message


@pytest.mark.asyncio
async def test_retry_track_time_start(retry, monkeypatch):
    registry = SimpleNamespace(
        get_entry=lambda name: SimpleNamespace(schema={"parameters": {"required": ["project"]}}) if name == "track_time" else None,
        dispatch=lambda name, args, **kwargs: json.dumps(
            {"success": True, "project": args["project"], "action": args.get("action", "start")}
        ),
    )
    monkeypatch.setitem(__import__("sys").modules, "tools.registry", SimpleNamespace(registry=registry))

    message = await retry.retry(
        original_message="Track my time on this project",
        tool_name="track_time",
    )
    assert "Timer started" in message
    assert "this project" in message


@pytest.mark.asyncio
async def test_retry_missing_tool_returns_error(retry, monkeypatch):
    registry = SimpleNamespace(get_entry=lambda _name: None, dispatch=lambda *_args, **_kwargs: "{}")
    monkeypatch.setitem(__import__("sys").modules, "tools.registry", SimpleNamespace(registry=registry))

    message = await retry.retry(
        original_message="do something",
        tool_name="missing_tool",
    )
    assert "not yet available" in message
