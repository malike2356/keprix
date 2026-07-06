"""Tests for the App Foundation SDK."""

from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.server import create_app
from keprix.public_api.keys import ApiKeyStore, CreateApiKeyRequest
from keprix.sdk.store import SdkStore


INVOICE_DOMAIN = {
    "name": "invoicing",
    "entities": [
        {
            "name": "Client",
            "fields": [{"name": "name", "type": "string", "required": True}],
            "operations": [{"name": "delete", "confirmation_required": True}],
        },
        {
            "name": "Invoice",
            "fields": [
                {"name": "client_id", "type": "foreign_key", "entity": "Client", "required": True},
                {"name": "amount", "type": "decimal", "required": True},
            ],
            "operations": [{"name": "create"}, {"name": "send", "confirmation_required": True}],
        },
    ],
}


@pytest.fixture(autouse=True)
def disable_database(monkeypatch):
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.observability.metrics.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.public_api.auth.effective_access_level", lambda: "developer")


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.fixture
def key_store(tmp_path, monkeypatch):
    store = ApiKeyStore(path=tmp_path / "api_keys.json")
    monkeypatch.setattr("keprix.public_api.keys.get_api_key_store", lambda: store)
    monkeypatch.setattr("keprix.public_api.auth.get_api_key_store", lambda: store)
    monkeypatch.setattr("keprix.public_api.developer_routes.get_api_key_store", lambda: store)
    return store


@pytest.fixture
def sdk_store(tmp_path, monkeypatch):
    store = SdkStore(base_dir=tmp_path / "sdk")
    monkeypatch.setattr("keprix.sdk.store.get_sdk_store", lambda: store)
    monkeypatch.setattr("keprix.sdk.routes.get_sdk_store", lambda: store)
    return store


@pytest.mark.asyncio
async def test_register_app(client, key_store, sdk_store):
    created = key_store.create(CreateApiKeyRequest(name="sdk"))
    response = await client.post(
        "/api/sdk/apps/register",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"name": "invoice-test", "version": "1.0.0", "domain": INVOICE_DOMAIN},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["app_id"]
    assert payload["name"] == "invoice-test"


@pytest.mark.asyncio
async def test_execute_create_invoice(client, key_store, sdk_store):
    created = key_store.create(CreateApiKeyRequest(name="sdk"))
    reg = await client.post(
        "/api/sdk/apps/register",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"name": "invoice-exec", "version": "1.0.0", "domain": INVOICE_DOMAIN},
    )
    app_id = reg.json()["app_id"]
    response = await client.post(
        "/api/sdk/execute",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"app_id": app_id, "message": "create invoice for James £500"},
    )
    assert response.status_code == 200
    plan = response.json()
    assert plan["steps"][0]["entity"] == "Invoice"
    assert plan["steps"][0]["operation"] == "create"
    assert plan["steps"][0]["fields"]["client"] == "James"
    assert plan["steps"][0]["fields"]["amount"] == 500.0


@pytest.mark.asyncio
async def test_execute_delete_requires_confirmation(client, key_store, sdk_store):
    created = key_store.create(CreateApiKeyRequest(name="sdk"))
    reg = await client.post(
        "/api/sdk/apps/register",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"name": "invoice-del", "version": "1.0.0", "domain": INVOICE_DOMAIN},
    )
    app_id = reg.json()["app_id"]
    response = await client.post(
        "/api/sdk/execute",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"app_id": app_id, "message": "delete all clients"},
    )
    plan = response.json()
    assert plan["requires_confirmation"] is True
    assert plan["steps"][0]["operation"] == "delete"


@pytest.mark.asyncio
async def test_list_apps_admin(client, key_store, sdk_store):
    created = key_store.create(CreateApiKeyRequest(name="sdk"))
    await client.post(
        "/api/sdk/apps/register",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"name": "listed-app", "version": "1.0.0", "domain": INVOICE_DOMAIN},
    )
    response = await client.get("/api/sdk/apps")
    assert response.status_code == 200
    apps = response.json()["apps"]
    assert any(app["name"] == "listed-app" for app in apps)


@pytest.mark.asyncio
async def test_event_bus_used_by_execute(app, key_store, sdk_store, monkeypatch):
    """Execute publishes to the SDK event bus (SSE wiring is covered in test_events)."""
    from keprix.sdk.events import SdkEventBus

    bus = SdkEventBus()
    monkeypatch.setattr("keprix.sdk.routes.get_sdk_event_bus", lambda: bus)
    created = key_store.create(CreateApiKeyRequest(name="sdk"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post(
            "/api/sdk/apps/register",
            headers={"Authorization": f"Bearer {created.secret}"},
            json={"name": "bus-app", "version": "1.0.0", "domain": INVOICE_DOMAIN},
        )
        app_id = reg.json()["app_id"]
        queue = bus.subscribe(app_id)
        await client.post(
            "/api/sdk/execute",
            headers={"Authorization": f"Bearer {created.secret}"},
            json={"app_id": app_id, "message": "create invoice for James £500"},
        )
        payload = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert payload["steps"][0]["entity"] == "Invoice"
