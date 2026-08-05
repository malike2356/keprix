"""Scout lifecycle webhook client tests."""

from __future__ import annotations

import pytest

from keprix.integrations.scout_lifecycle_client import emit_scout_lifecycle_event


@pytest.mark.asyncio
async def test_disabled_when_labyrinth_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LABYRINTH_ENABLED", raising=False)
    monkeypatch.setenv("LABYRINTH_SCOUT_WEBHOOK_URL", "https://scout.example/webhook")

    assert await emit_scout_lifecycle_event("playbook_published", {}, workspace_id="default") is None


@pytest.mark.asyncio
async def test_mock_http_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, url, json, headers):
            calls.append({"url": url, "json": json, "headers": headers})
            return FakeResponse()

    monkeypatch.setenv("LABYRINTH_ENABLED", "1")
    monkeypatch.setenv("LABYRINTH_SCOUT_WEBHOOK_URL", "https://scout.example/webhook")
    monkeypatch.setenv("LABYRINTH_SCOUT_API_KEY", "secret")
    monkeypatch.setattr("httpx.AsyncClient", FakeClient)

    event_id = await emit_scout_lifecycle_event("playbook_published", {"x": 1}, workspace_id="ws")

    assert event_id and event_id.startswith("evt_")
    assert calls[0]["url"] == "https://scout.example/webhook"
    assert calls[0]["headers"]["Authorization"] == "Bearer secret"
    assert calls[0]["json"]["payload"] == {"x": 1}
