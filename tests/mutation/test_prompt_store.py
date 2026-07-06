"""Tests for PromptStore (Prompt 152)."""

from __future__ import annotations

import pytest

from keprix.mutation.config import get_mutation_settings
from keprix.mutation.prompt_store import PromptStore, get_prompt_store
from keprix.mutation.store import MutationStore


@pytest.fixture
def prompt_store(tmp_path, monkeypatch):
    get_mutation_settings.cache_clear()
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.mutation.store.get_session_factory", lambda: None)
    mutation_store = MutationStore(sqlite_path=tmp_path / "mutation.db")
    store = PromptStore(sqlite_path=tmp_path / "mutation.db", mutation_store=mutation_store)
    monkeypatch.setattr("keprix.mutation.store._store", mutation_store)
    monkeypatch.setattr("keprix.mutation.store.get_mutation_store", lambda: mutation_store)
    monkeypatch.setattr("keprix.mutation.prompt_store._store", store)
    monkeypatch.setattr("keprix.mutation.prompt_store.get_prompt_store", lambda: store)
    return store


def test_get_active_returns_none_when_empty(prompt_store):
    assert prompt_store.get_active_prompt("default", "default") is None


def test_get_active_or_default_returns_default_when_empty(prompt_store):
    default = "You are a helpful agent."
    assert prompt_store.get_active_or_default("default", "default", default) == default


def test_stage_auto_approves_above_threshold(prompt_store):
    version = prompt_store.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Evolved prompt",
        rationale="user correction",
        confidence=0.90,
        auto_approve_threshold=0.85,
    )
    assert version.is_active is True
    assert prompt_store.get_active_prompt("default", "default") == "Evolved prompt"


def test_stage_remains_staged_below_threshold(prompt_store):
    version = prompt_store.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Staged prompt",
        rationale="low eval",
        confidence=0.70,
        auto_approve_threshold=0.85,
    )
    assert version.is_active is False
    assert prompt_store.get_active_prompt("default", "default") is None


def test_activate_version_deactivates_previous(prompt_store):
    first = prompt_store.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Version one",
        rationale="first",
        confidence=0.90,
        auto_approve_threshold=0.85,
    )
    second = prompt_store.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Version two",
        rationale="second",
        confidence=0.70,
        auto_approve_threshold=0.85,
    )
    activated = prompt_store.activate_version(second.id, activated_by="operator")
    assert activated.is_active is True
    refreshed_first = prompt_store.get_version(first.id)
    assert refreshed_first is not None
    assert refreshed_first.is_active is False
    assert prompt_store.get_active_prompt("default", "default") == "Version two"


def test_rollback_restores_prior_active(prompt_store):
    prompt_store.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Version one",
        rationale="first",
        confidence=0.90,
        auto_approve_threshold=0.85,
    )
    prompt_store.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Version two",
        rationale="second",
        confidence=0.90,
        auto_approve_threshold=0.85,
    )
    restored = prompt_store.rollback_to_previous("default", "default", rolled_back_by="operator")
    assert restored is not None
    assert restored.content == "Version one"
    assert restored.is_active is True
    assert prompt_store.get_active_prompt("default", "default") == "Version one"


def test_get_history_newest_first(prompt_store):
    prompt_store.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Version one",
        rationale="first",
        confidence=0.70,
        auto_approve_threshold=0.85,
    )
    prompt_store.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Version two",
        rationale="second",
        confidence=0.70,
        auto_approve_threshold=0.85,
    )
    history = prompt_store.get_history("default", "default", limit=10)
    assert len(history) == 2
    assert history[0].version > history[1].version


def test_fallback_when_db_unavailable(prompt_store, monkeypatch):
    def _boom(*_args, **_kwargs):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(prompt_store, "_get_active_version", _boom)
    assert prompt_store.get_active_prompt("default", "default") is None
    assert prompt_store.get_active_or_default("default", "default", "DEFAULT") == "DEFAULT"
