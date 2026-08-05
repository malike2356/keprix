"""VirtualTranscript unit tests (Prompt 203)."""

from __future__ import annotations

import asyncio

import pytest

from keprix.tui.transcript_store import TranscriptItem, TranscriptStore
from keprix.tui.widgets.virtual_transcript import VirtualTranscript


def test_sticky_tail_follows_new_append() -> None:
    store = TranscriptStore()
    transcript = VirtualTranscript(store=store)
    transcript.at_bottom = True
    transcript._sticky_follow = True
    transcript._batch_depth = 1
    for index in range(10):
        store.append(
            TranscriptItem.create(role="system", plain_text=f"line {index}", body=f"line {index}")
        )
    transcript.end_batch()
    assert transcript.at_bottom is True


def test_batch_append_defers_refresh_until_end() -> None:
    store = TranscriptStore()
    transcript = VirtualTranscript(store=store)
    transcript._batch_depth = 1
    transcript.append_system("one")
    transcript.append_system("two")
    assert transcript._mount_start == -1
    transcript.end_batch()


@pytest.mark.asyncio
async def test_virtual_transcript_mounts_bounded_rows() -> None:
    from textual.app import App, ComposeResult

    class Host(App):
        def compose(self) -> ComposeResult:
            store = TranscriptStore()
            for index in range(200):
                store.append(
                    TranscriptItem.create(
                        role="system",
                        plain_text=f"msg {index}",
                        body=f"msg {index}",
                    )
                )
            yield VirtualTranscript(id="message-log", store=store)

    app = Host()
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        transcript = app.query_one("#message-log", VirtualTranscript)
        await asyncio.sleep(0.05)
        assert len(transcript.store.items) == 200
        assert transcript.mounted_row_count <= 120


@pytest.mark.asyncio
async def test_copy_source_uses_full_store_not_mounted_rows() -> None:
    from textual.app import App, ComposeResult

    store = TranscriptStore()
    store.append(TranscriptItem.create(role="user", plain_text="You: alpha", body="alpha"))
    store.append(TranscriptItem.create(role="agent", plain_text="keprix: beta", body="beta"))

    class Host(App):
        def compose(self) -> ComposeResult:
            yield VirtualTranscript(id="message-log", store=store)

    app = Host()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        transcript = app.query_one("#message-log", VirtualTranscript)
        assert transcript.store.full_plain_text() == "You: alpha\nkeprix: beta"
        assert transcript.mounted_row_count <= 2
