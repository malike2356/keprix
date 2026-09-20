"""First-run LLM list comes from the CLI provider registry, not a named default."""

from __future__ import annotations

from keprix.setup.wizard import apply_wizard_provider_key, wizard_llm_providers, wizard_status


def test_wizard_llm_providers_are_registry_api_key_ids():
    rows = wizard_llm_providers()
    assert rows
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))
    assert rows == sorted(rows, key=lambda row: (row["name"].lower(), row["id"]))
    assert all(row["name"] for row in rows)


def test_wizard_status_exposes_providers_without_a_default():
    status = wizard_status()
    assert "providers" in status
    assert status["providers"] == wizard_llm_providers()
    assert "default_provider" not in status


def test_apply_wizard_provider_key_uses_selected_registry_id(monkeypatch):
    saved: list[tuple[str, str]] = []
    activated: list[tuple[str, str]] = []
    monkeypatch.setattr("keprix.setup.wizard._persist_provider_env", lambda key, value: saved.append((key, value)))
    monkeypatch.setattr(
        "keprix.setup.wizard._set_active_provider",
        lambda provider_id, base_url: activated.append((provider_id, base_url)),
    )
    rows = wizard_llm_providers()
    chosen = rows[0]
    payload = apply_wizard_provider_key(chosen["id"], "test-key-123")
    assert payload["ok"] is True
    assert payload["provider"] == chosen["id"]
    assert saved
    assert activated[0][0] == chosen["id"]
