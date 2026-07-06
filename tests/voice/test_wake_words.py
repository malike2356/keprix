"""Prompt 46 voice wake word tests."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.voice.bus import broadcast, clear_nodes_for_tests, register_node_status, subscribe
from keprix.voice.detector import WakeWordDetector
from keprix.voice.service import get_wake_registry, reset_wake_registry_for_tests
from keprix.voice.wake import WAKE_WORD_DEFAULTS, normalize_triggers


@pytest.fixture
def wake_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    reset_wake_registry_for_tests()
    clear_nodes_for_tests()
    storage = tmp_path / "voicewake.json"
    registry = get_wake_registry(storage)

    def _get_registry(storage_path=None):
        return registry

    monkeypatch.setattr("keprix.voice.service.get_wake_registry", _get_registry)
    monkeypatch.setattr("keprix.voice.routes.get_wake_registry", _get_registry)
    monkeypatch.setattr("keprix.voice.gateway_handlers.get_wake_registry", _get_registry)
    return registry, storage


def test_normalize_lowercase_and_drop_empty():
    assert normalize_triggers(["Hey keprix", "computer", ""]) == ["hey keprix", "computer"]


def test_normalize_enforces_max_count():
    triggers = [f"word{i}" for i in range(11)]
    assert len(normalize_triggers(triggers)) == 10


def test_normalize_empty_restores_defaults():
    assert normalize_triggers([]) == list(WAKE_WORD_DEFAULTS)


def test_registry_set_broadcasts(wake_env):
    registry, _storage = wake_env
    events: list[dict] = []
    subscribe(events.append)
    saved = registry.set(["Hey keprix", "computer", ""])
    assert saved == ["hey keprix", "computer"]
    assert events[-1]["method"] == "voicewake.updated"
    assert events[-1]["triggers"] == saved


def test_detector_trigger_matching():
    detector = WakeWordDetector(["hey keprix", "keprix"])
    assert detector.is_triggered("hey keprix what time is it") is True
    assert detector.is_triggered("hello, what time is it") is False


def test_detector_update_triggers_immediate():
    detector = WakeWordDetector(["keprix"])
    assert detector.is_triggered("hey keprix") is True
    detector.update_triggers(["computer"])
    assert detector.is_triggered("hey keprix") is False
    assert detector.is_triggered("computer please help") is True


def test_registry_reset_restores_defaults(wake_env):
    registry, storage = wake_env
    registry.set(["custom"])
    registry.reset()
    assert registry.get() == list(WAKE_WORD_DEFAULTS)
    payload = json.loads(storage.read_text(encoding="utf-8"))
    assert payload["triggers"] == list(WAKE_WORD_DEFAULTS)


def test_registry_atomic_write(wake_env):
    registry, storage = wake_env
    registry.set(["alpha"])
    assert storage.exists()
    assert not storage.with_suffix(".json.tmp").exists()


def test_offline_node_gets_updated_list_on_next_get(wake_env):
    registry, _storage = wake_env
    registry.set(["offline-sync"])
    fresh = get_wake_registry(_storage)
    assert fresh.get() == ["offline-sync"]


def test_node_status_platform_availability():
    register_node_status("desktop-1", platform="desktop", wake_enabled=True, permission_granted=True)
    register_node_status("web-1", platform="web", wake_enabled=False, permission_granted=False)
    from keprix.voice.bus import list_node_statuses

    rows = {row["node_id"]: row for row in list_node_statuses()}
    assert rows["desktop-1"]["wake_detection_available"] is True
    assert rows["web-1"]["wake_detection_available"] is False


@pytest.mark.asyncio
async def test_api_put_and_reset(wake_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        put = await client.put("/api/voice/wake-words", json={"triggers": ["Hey keprix", "assistant"]})
        assert put.status_code == 200
        assert put.json()["triggers"] == ["hey keprix", "assistant"]

        reset = await client.post("/api/voice/wake-words/reset")
        assert reset.status_code == 200
        assert reset.json()["triggers"] == list(WAKE_WORD_DEFAULTS)


@pytest.mark.asyncio
async def test_api_put_empty_restores_defaults(wake_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put("/api/voice/wake-words", json={"triggers": []})
        assert response.status_code == 200
        assert response.json()["triggers"] == list(WAKE_WORD_DEFAULTS)
