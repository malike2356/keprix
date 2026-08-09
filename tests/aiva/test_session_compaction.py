from __future__ import annotations

import pytest

from keprix.aiva.session_compaction import (
    SUMMARY_MARKER,
    extract_previous_summary,
    is_summary_message,
    maybe_compact_messages,
    maybe_compact_session_store,
)
from keprix.agent.carina_bridge import SessionStore, _persistable_messages


def _msgs(n: int) -> list[dict]:
    out: list[dict] = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        out.append({"role": role, "content": f"message-{i}: topic decision pending"})
    return out


def test_compacts_after_threshold_keeps_recent() -> None:
    messages = _msgs(30)

    def summarizer(system: str, user: str) -> str:
        assert "compress" in system.lower() or "Summarise" in system or "summary" in system.lower()
        assert "message-0" in user
        return "User discussed early topics and left pending actions."

    compacted, changed = maybe_compact_messages(
        messages,
        summarizer=summarizer,
        threshold=20,
        batch_size=20,
        keep_recent=20,
    )
    assert changed is True
    assert is_summary_message(compacted[0])
    assert SUMMARY_MARKER in compacted[0]["content"]
    assert "pending actions" in compacted[0]["content"]
    raw = [m for m in compacted if not is_summary_message(m)]
    assert len(raw) == 20
    assert raw[0]["content"].startswith("message-10")
    assert raw[-1]["content"].startswith("message-29")


def test_merges_previous_summary_instead_of_stacking() -> None:
    prior_summary = {
        "role": "system",
        "content": f"{SUMMARY_MARKER}\nEarlier: calendar reschedule pending.",
        "aiva_summary": True,
    }
    messages = [prior_summary, *_msgs(25)]

    def summarizer(system: str, user: str) -> str:
        assert "calendar reschedule pending" in user
        return "Merged summary covering calendar and later topics."

    compacted, changed = maybe_compact_messages(
        messages,
        summarizer=summarizer,
        threshold=20,
        batch_size=20,
        keep_recent=20,
    )
    assert changed is True
    summaries = [m for m in compacted if is_summary_message(m)]
    assert len(summaries) == 1
    assert "Merged summary" in summaries[0]["content"]
    assert extract_previous_summary(compacted).startswith("Merged summary")


def test_skips_when_under_threshold() -> None:
    messages = _msgs(10)
    compacted, changed = maybe_compact_messages(messages, summarizer=lambda s, u: "x")
    assert changed is False
    assert compacted == messages


def test_extractive_fallback_on_summarizer_failure() -> None:
    messages = _msgs(25)

    def boom(_system: str, _user: str) -> str:
        raise RuntimeError("no llm")

    compacted, changed = maybe_compact_messages(
        messages,
        summarizer=boom,
        threshold=20,
        keep_recent=20,
        batch_size=20,
    )
    assert changed is True
    assert is_summary_message(compacted[0])
    assert "user:" in compacted[0]["content"].lower() or "message-" in compacted[0]["content"]


def test_persistable_keeps_aiva_summary() -> None:
    messages = [
        {"role": "system", "content": "live lean prompt"},
        {
            "role": "system",
            "content": f"{SUMMARY_MARKER}\nOld facts",
            "aiva_summary": True,
        },
        {"role": "user", "content": "hi"},
    ]
    # Leading live prompt dropped; if summary were leading it must be kept.
    only_summary_first = [
        {
            "role": "system",
            "content": f"{SUMMARY_MARKER}\nOld facts",
            "aiva_summary": True,
        },
        {"role": "user", "content": "hi"},
    ]
    kept = _persistable_messages(only_summary_first)
    assert kept[0]["aiva_summary"] is True
    assert kept[1]["content"] == "hi"
    # conversation-shaped: first system is live prompt
    assert _persistable_messages(messages)[0]["content"] == f"{SUMMARY_MARKER}\nOld facts"


@pytest.mark.asyncio
async def test_session_store_compaction_roundtrip() -> None:
    store = SessionStore()
    await store.save("ws", "s1", _msgs(28))

    def summarizer(_s: str, _u: str) -> str:
        return "Compressed history about earlier asks."

    changed = await maybe_compact_session_store(store, "ws", "s1", summarizer=summarizer)
    assert changed is True
    loaded = await store.get("ws", "s1")
    assert is_summary_message(loaded[0])
    assert len([m for m in loaded if not is_summary_message(m)]) == 20
