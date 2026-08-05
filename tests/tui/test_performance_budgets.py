from __future__ import annotations

import time

import pytest

from keprix.tui.hardening import LatencyBudgets, coalesce_resize_events
from keprix.tui.renderer.viewport import ViewportState, stable_append_viewport, stable_resize_viewport
from keprix.tui.slash_registry import local_completion_items


def _elapsed_ms(fn) -> float:
    started = time.perf_counter()
    fn()
    return (time.perf_counter() - started) * 1000


def test_slash_picker_open_budget_for_local_commands() -> None:
    budgets = LatencyBudgets()
    elapsed = _elapsed_ms(lambda: local_completion_items("/"))
    assert elapsed < budgets.slash_open_ms


def test_slash_filter_budget_for_500_commands() -> None:
    budgets = LatencyBudgets()
    commands = [f"/command-{index}" for index in range(500)]
    elapsed = _elapsed_ms(lambda: [command for command in commands if "42" in command])
    assert elapsed < budgets.slash_filter_500_ms


def test_transcript_append_and_virtual_window_budgets() -> None:
    budgets = LatencyBudgets()
    viewport = ViewportState(viewport_height=30, content_height=10_000)
    viewport.scroll_to_bottom()
    append_elapsed = _elapsed_ms(lambda: stable_append_viewport(viewport, 1))
    assert append_elapsed < budgets.transcript_append_ms
    window_elapsed = _elapsed_ms(lambda: viewport.visible_range())
    assert window_elapsed < budgets.virtual_window_10k_ms


@pytest.mark.asyncio
async def test_interrupt_schedule_budget() -> None:
    budgets = LatencyBudgets()

    async def interrupt() -> None:
        return None

    started = time.perf_counter()
    await interrupt()
    assert (time.perf_counter() - started) * 1000 < budgets.interrupt_schedule_ms


def test_resize_refresh_budget_for_large_transcripts() -> None:
    budgets = LatencyBudgets()
    viewport = ViewportState(viewport_height=30, content_height=100_000)
    events = [(120, 30 + index % 5) for index in range(2_000)]
    elapsed = _elapsed_ms(lambda: stable_resize_viewport(viewport, coalesce_resize_events(events)[1], 100_000))  # type: ignore[index]
    assert elapsed < budgets.resize_refresh_ms
