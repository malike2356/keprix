from __future__ import annotations

import sys

from keprix.tui.composer import MessageQueue
from keprix.tui.hardening import MemoryBudgets, queue_payload_bytes
from keprix.tui.renderer.snapshots import normalize_snapshot
from keprix.tui.runtime_events import MessageRuntimeMetadata
from keprix.tui.runtime_store import RuntimeStore


def test_runtime_store_message_and_api_lists_are_capped() -> None:
    store = RuntimeStore()
    for index in range(1_000):
        store.add_message_metadata(MessageRuntimeMetadata(message_id=str(index)))
    assert len(store.messages) == 500


def test_queue_memory_budget_for_1k_messages() -> None:
    budgets = MemoryBudgets()
    queue = MessageQueue()
    for index in range(1_000):
        queue.enqueue(f"message {index}")
    payload = queue.snapshot()
    assert queue_payload_bytes(payload) < budgets.queue_bytes


def test_render_snapshot_memory_budget() -> None:
    budgets = MemoryBudgets()
    snapshot = normalize_snapshot("\n".join(f"line {index}   " for index in range(10_000)))
    assert sys.getsizeof(snapshot) < budgets.render_snapshot_bytes
