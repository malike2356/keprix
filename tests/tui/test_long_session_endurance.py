from __future__ import annotations

from keprix.tui.composer import InputHistory, MessageQueue
from keprix.tui.renderer.viewport import ViewportState
from keprix.tui.runtime_store import RuntimeStore


def test_10k_messages_and_100k_line_virtual_estimate() -> None:
    viewport = ViewportState(viewport_height=40, content_height=100_000)
    viewport.scroll_to_bottom()
    assert viewport.visible_range() == (99_960, 100_000)
    messages = [f"message {index}" for index in range(10_000)]
    assert messages[0] == "message 0"
    assert messages[-1] == "message 9999"


def test_500_tool_events_and_100_subagents_do_not_break_runtime_store() -> None:
    store = RuntimeStore()
    store.start_turn(session_id="s1")
    for index in range(500):
        store.start_tool(f"tool-{index}", call_id=str(index))
        store.finish_tool(f"tool-{index}", call_id=str(index), status="done")
    for index in range(100):
        parent = str(index // 2) if index else ""
        store.spawn_subagent(str(index), label=f"agent-{index}", parent_id=parent)
        if index % 2 == 0:
            store.finish_subagent(str(index), status="done")
    assert len(store.tools) == 500
    assert len(store.subagents) == 100
    assert "Tools: 0 running, 500 done" in store.summary_lines()


def test_1k_queue_and_10k_input_history_keep_user_text() -> None:
    queue = MessageQueue()
    for index in range(1_000):
        queue.enqueue(f"queued {index}")
    assert len(queue) == 1_000
    assert queue.pop() == "queued 0"
    history = InputHistory(max_items=10_000)
    for index in range(10_500):
        history.push(f"input {index}")
    snapshot = history.snapshot()
    assert len(snapshot) == 10_000
    assert snapshot[0] == "input 500"
    assert snapshot[-1] == "input 10499"
