"""Tests for extensions/lifecycle.py."""

from __future__ import annotations

import pytest

from keprix.extensions.base import KeprixExtension
from keprix.extensions.lifecycle import ExtensionLifecycle


class _MockExt(KeprixExtension):
    def __init__(self, name: str):
        self.name = name
        self.display_name = name.title()
        self.version = "1.0.0"
        self.keprix_min_version = "0.3.0"
        self.started = False
        self.stopped = False
        self.routes = []
        self.domain_tools = ["tool_a"]
        self.personas = []
        self.ui_components = []

    async def on_startup(self) -> None:
        self.started = True

    async def on_shutdown(self) -> None:
        self.stopped = True


@pytest.fixture
def lifecycle():
    return ExtensionLifecycle()


@pytest.mark.asyncio
async def test_startup_calls_on_startup(lifecycle):
    ext = _MockExt("abbis")
    lifecycle.register(ext)
    started = await lifecycle.startup()
    assert "abbis" in started
    assert ext.started is True


@pytest.mark.asyncio
async def test_shutdown_calls_on_shutdown(lifecycle):
    ext = _MockExt("abbis")
    lifecycle.register(ext)
    await lifecycle.startup()
    await lifecycle.shutdown()
    assert ext.stopped is True


@pytest.mark.asyncio
async def test_shutdown_skips_unstarted_extensions(lifecycle):
    ext = _MockExt("abbis")
    lifecycle.register(ext)
    await lifecycle.shutdown()  # never started
    assert ext.stopped is False


@pytest.mark.asyncio
async def test_startup_continues_after_extension_error(lifecycle):
    class _FailExt(_MockExt):
        async def on_startup(self) -> None:
            raise RuntimeError("startup error")

    good = _MockExt("good")
    lifecycle.register(_FailExt("bad"))
    lifecycle.register(good)
    started = await lifecycle.startup()
    assert "good" in started
    assert "bad" not in started
    assert good.started is True


@pytest.mark.asyncio
async def test_register_all(lifecycle):
    exts = [_MockExt("a"), _MockExt("b")]
    lifecycle.register_all(exts)
    started = await lifecycle.startup()
    assert set(started) == {"a", "b"}


def test_all_tools_aggregates(lifecycle):
    lifecycle.register(_MockExt("a"))
    lifecycle.register(_MockExt("b"))
    tools = lifecycle.all_tools()
    assert len(tools) == 2  # each ext provides ["tool_a"]


def test_summary(lifecycle):
    lifecycle.register(_MockExt("x"))
    s = lifecycle.summary()
    assert "x" in s["registered"]
    assert s["total_tools"] == 1
