"""Support ticket tests."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.support.store import SupportStore
from keprix.support.tickets import create_ticket, export_ticket


@pytest.fixture()
def support_store(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    import keprix.support.store as store_module

    store = SupportStore(base_dir=tmp_path / "support")
    store_module._store = store
    return store


def test_support_ticket_can_be_exported(support_store) -> None:
    ticket = create_ticket(
        category="bug",
        subject="Export test",
        description="Steps to reproduce",
    )
    exported = export_ticket(ticket["id"])
    assert exported is not None
    payload = json.loads(exported)
    assert payload["ticket"]["subject"] == "Export test"


@pytest.mark.asyncio
async def test_create_ticket_route(support_store) -> None:
    headers = {"Authorization": "Bearer test-api-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/support/tickets",
            headers=headers,
            json={
                "category": "installation",
                "subject": "Cannot start API",
                "description": "Service exits on boot",
                "attach_diagnostics": False,
            },
        )
        assert response.status_code == 200
        assert response.json()["ticket"]["category"] == "installation"
