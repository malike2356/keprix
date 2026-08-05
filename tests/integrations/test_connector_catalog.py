"""Connector marketplace catalog tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.integrations.connector_audit import enrich_run_event
from keprix.integrations.connector_catalog import load_connector_catalog


def test_catalog_minimum_count() -> None:
    assert len(load_connector_catalog()) >= 20


def test_each_entry_complete() -> None:
    for entry in load_connector_catalog():
        assert entry.icon
        assert entry.auth_pattern
        assert entry.scout_audit_class
        assert entry.sample_playbook_node
        assert entry.sample_playbook_node.get("type") in {"agent_task", "http"}
        assert isinstance(entry.sample_playbook_node.get("data"), dict)


@pytest.mark.asyncio
async def test_get_unknown_404() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/integrations/catalog/not_real")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_install_notion_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, str] = {}

    class FakeMcpEntry:
        name = "notion"

    def fake_get_entry(name: str):
        called["get_entry"] = name
        return FakeMcpEntry()

    def fake_install_entry(entry):
        called["install_entry"] = entry.name

    monkeypatch.setattr("keprix_cli.mcp_catalog.get_entry", fake_get_entry)
    monkeypatch.setattr("keprix_cli.mcp_catalog.install_entry", fake_install_entry)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/integrations/catalog/notion/install", json={"confirm": True})

    assert response.status_code == 200
    assert response.json()["status"] == "installed"
    assert called == {"get_entry": "notion", "install_entry": "notion"}


def test_audit_class_enrichment() -> None:
    event = enrich_run_event(
        {"node": "send"},
        step_config={"connector_id": "telegram", "tools": ["send_telegram_message"]},
    )

    assert event["connector_id"] == "telegram"
    assert event["scout_audit_class"] == "messaging_send"
