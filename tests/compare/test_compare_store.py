"""Compare store persistence tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.compare.store import CompareStore, reset_compare_store


@pytest.fixture
def isolated_store(tmp_path: Path):
    store = CompareStore(sqlite_path=tmp_path / "compare.db")
    reset_compare_store(store)
    yield store
    reset_compare_store(None)


def test_create_and_vote_persist_across_store_instances(tmp_path: Path):
    db_path = tmp_path / "compare.db"
    first = CompareStore(sqlite_path=db_path)
    record = first.create(
        user_id="alice",
        prompt="Explain RAG",
        model_a="deepseek:deepseek-chat",
        model_b="openai:gpt-4.1-mini",
        response_a="answer a",
        response_b="answer b",
        latency_ms_a=120,
        latency_ms_b=140,
    )
    voted = first.vote(record.id, "alice", "b")
    assert voted is not None
    assert voted.winner == "b"

    second = CompareStore(sqlite_path=db_path)
    loaded = second.get(record.id, "alice")
    assert loaded is not None
    assert loaded.response_a == "answer a"
    assert loaded.latency_ms_b == 140
    assert loaded.winner == "b"


def test_leaderboard_pair_and_model_stats(isolated_store: CompareStore):
    record = isolated_store.create(
        user_id="alice",
        prompt="test",
        model_a="deepseek:deepseek-chat",
        model_b="openai:gpt-4.1-mini",
        response_a="a",
        response_b="b",
    )
    isolated_store.vote(record.id, "alice", "a")

    pairs = isolated_store.leaderboard()
    assert pairs
    assert pairs[0]["comparisons"] == 1
    assert pairs[0]["a_win_rate_pct"] == 100.0

    models = isolated_store.model_leaderboard()
    assert len(models) == 2
    winner = next(row for row in models if row["model_id"] == "deepseek:deepseek-chat")
    assert winner["wins"] == 1
    assert winner["win_rate_pct"] == 100.0


def test_list_for_user_scoped(isolated_store: CompareStore):
    isolated_store.create(
        user_id="alice",
        prompt="one",
        model_a="a:1",
        model_b="b:2",
        response_a="x",
        response_b="y",
    )
    isolated_store.create(
        user_id="bob",
        prompt="two",
        model_a="a:1",
        model_b="b:2",
        response_a="x",
        response_b="y",
    )
    assert len(isolated_store.list_for_user("alice")) == 1
    assert len(isolated_store.list_for_user("bob")) == 1
