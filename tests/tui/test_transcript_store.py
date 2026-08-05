"""TranscriptStore unit tests (Prompt 203)."""

from __future__ import annotations

from keprix.tui.transcript_store import (
    TranscriptItem,
    TranscriptStore,
    estimate_item_height,
    item_from_transcript_line,
)


def test_prefix_heights_start_at_zero_and_are_monotonic() -> None:
    store = TranscriptStore()
    store.append(TranscriptItem.create(role="system", plain_text="one", body="one"))
    store.append(TranscriptItem.create(role="user", plain_text="You: hi", body="hi"))
    store.append(TranscriptItem.create(role="agent", plain_text="keprix: hello", body="hello"))
    assert store.prefix_heights[0] == 0
    assert store.prefix_heights[1] == store.items[0].estimated_height
    assert store.prefix_heights[2] == store.items[0].estimated_height + store.items[1].estimated_height
    assert TranscriptStore.prefix_heights_monotonic(store.prefix_heights)


def test_height_cache_reuse_after_append() -> None:
    store = TranscriptStore()
    for index in range(5):
        store.append(TranscriptItem.create(role="system", plain_text=f"line {index}", body=f"line {index}"))
    first_prefix = list(store.prefix_heights)
    store.append(TranscriptItem.create(role="system", plain_text="line 5", body="line 5"))
    assert store.prefix_heights[: len(first_prefix)] == first_prefix
    assert store.prefix_heights[-1] == first_prefix[-1] + store.items[-2].estimated_height


def test_mount_window_caps_visible_items() -> None:
    store = TranscriptStore()
    for index in range(1000):
        store.append(
            TranscriptItem.create(
                role="system",
                plain_text=f"message {index}",
                body=f"message {index}",
            )
        )
    start, end = store.mount_index_range(scroll_y=0, viewport_height=20, max_window=120, overscan=8)
    assert end - start + 1 <= 120


def test_visible_range_finds_middle_segment() -> None:
    store = TranscriptStore()
    for index in range(50):
        store.append(
            TranscriptItem.create(
                role="system",
                plain_text=f"row {index}",
                body=f"row {index}",
            )
        )
    midpoint = store.total_height // 2
    first, last = store.visible_index_range(midpoint, 10)
    assert 0 <= first <= last < len(store.items)


def test_full_plain_text_for_copy() -> None:
    store = TranscriptStore()
    store.append(TranscriptItem.create(role="user", plain_text="You: ping", body="ping"))
    store.append(TranscriptItem.create(role="agent", plain_text="keprix: pong", body="pong"))
    assert store.full_plain_text() == "You: ping\nkeprix: pong"


def test_item_from_transcript_line_roles() -> None:
    user = item_from_transcript_line("You: hello")
    assert user is not None
    assert user.role == "user"
    agent = item_from_transcript_line("keprix: hi")
    assert agent is not None
    assert agent.role == "agent"
    system = item_from_transcript_line("connected")
    assert system is not None
    assert system.role == "system"


def test_estimate_item_height_scales_with_body() -> None:
    short = estimate_item_height("system", "hi")
    long = estimate_item_height("system", "word " * 200)
    assert long > short


def test_store_trims_when_max_items_exceeded() -> None:
    store = TranscriptStore(max_items=3)
    for index in range(5):
        store.append(TranscriptItem.create(role="system", plain_text=f"m{index}", body=f"m{index}"))
    assert len(store.items) == 3
    assert store.archived_warning is True
    assert store.items[0].plain_text == "m2"
