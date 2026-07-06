"""Tests for PersonaMutationStore (Prompt 152)."""

from __future__ import annotations

import pytest

from keprix.mutation.config import get_mutation_settings
from keprix.mutation.persona_mutation_store import (
    PersonaMutationStore,
    get_persona_mutation_store,
    merge_persona_dict,
)
from keprix.mutation.prompt_store import PromptStore
from keprix.mutation.store import MutationStore
from keprix.personas.sage.persona import SAGE_PERSONA


@pytest.fixture
def persona_store(tmp_path, monkeypatch):
    get_mutation_settings.cache_clear()
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.mutation.store.get_session_factory", lambda: None)
    mutation_store = MutationStore(sqlite_path=tmp_path / "mutation.db")
    prompt_store = PromptStore(sqlite_path=tmp_path / "mutation.db", mutation_store=mutation_store)
    store = PersonaMutationStore(mutation_store=mutation_store, prompt_store=prompt_store)
    monkeypatch.setattr("keprix.mutation.store._store", mutation_store)
    monkeypatch.setattr("keprix.mutation.store.get_mutation_store", lambda: mutation_store)
    monkeypatch.setattr("keprix.mutation.prompt_store._store", prompt_store)
    monkeypatch.setattr("keprix.mutation.prompt_store.get_prompt_store", lambda: prompt_store)
    monkeypatch.setattr("keprix.mutation.persona_mutation_store._store", store)
    monkeypatch.setattr("keprix.mutation.persona_mutation_store.get_persona_mutation_store", lambda: store)
    return store


def test_get_overrides_empty_for_new_workspace(persona_store):
    assert persona_store.get_overrides("default", "SAGE") == {}


def test_stage_override_auto_approves(persona_store):
    record = persona_store.stage_override(
        workspace_id="default",
        persona_id="SAGE",
        field="description",
        new_value="Research specialist with stronger citation checks",
        rationale="improve clarity",
        confidence=0.90,
        auto_approve_threshold=0.85,
    )
    assert record.status == "approved"
    overrides = persona_store.get_overrides("default", "SAGE")
    assert overrides["description"] == "Research specialist with stronger citation checks"


def test_persona_load_merges_overrides(persona_store):
    persona_store.stage_override(
        workspace_id="default",
        persona_id="SAGE",
        field="system_prompt",
        new_value="You are SAGE with evolved instructions.",
        rationale="prompt evolution",
        confidence=0.90,
        auto_approve_threshold=0.85,
    )
    merged = merge_persona_dict(SAGE_PERSONA.to_dict(), "default")
    assert merged["system_prompt"] == "You are SAGE with evolved instructions."
    assert merged["system_prompt"] != SAGE_PERSONA.system_prompt()


def test_rollback_override_restores_static_default(persona_store):
    persona_store.stage_override(
        workspace_id="default",
        persona_id="SAGE",
        field="description",
        new_value="Temporary description",
        rationale="test",
        confidence=0.90,
        auto_approve_threshold=0.85,
    )
    rolled = persona_store.rollback_override("default", "SAGE", "description", rolled_back_by="test")
    assert rolled is not None
    assert persona_store.get_overrides("default", "SAGE") == {}
