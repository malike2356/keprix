"""Prompt 11 acceptance tests: email integration."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.email.mcp_server import _tools
from keprix.email.store import get_email_store, reset_email_store


@pytest.fixture(autouse=True)
def _reset_store():
    reset_email_store()
    yield
    reset_email_store()


@pytest.mark.asyncio
async def test_create_account_returns_201():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/email/accounts",
            json={
                "label": "Work",
                "email_address": "user@example.com",
                "imap_host": "imap.example.com",
                "imap_port": 993,
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "username": "user@example.com",
                "password": "secret",
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["email_address"] == "user@example.com"
    assert "password" not in data


@pytest.mark.asyncio
async def test_test_account_returns_folders():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/email/accounts",
            json={
                "email_address": "user@example.com",
                "imap_host": "imap.example.com",
                "smtp_host": "smtp.example.com",
                "username": "user@example.com",
                "password": "secret",
            },
        )
        account_id = created.json()["id"]
        with patch("keprix.email.routes.test_imap_smtp", return_value={"ok": True, "folders": ["INBOX"]}):
            response = await client.post(f"/api/email/accounts/{account_id}/test")
    assert response.status_code == 200
    assert response.json()["folders"] == ["INBOX"]


@pytest.mark.asyncio
async def test_inbox_unread_filter():
    store = get_email_store()
    account = await store.create_account(
        "local",
        {
            "email_address": "a@b.com",
            "imap_host": "i",
            "smtp_host": "s",
            "username": "a@b.com",
            "password": "x",
        },
    )
    await store.upsert_email(
        account,
        {
            "message_id": "m1",
            "uid": 1,
            "folder": "INBOX",
            "from_address": "sender@example.com",
            "to_addresses": ["a@b.com"],
            "subject": "Hello",
            "body_text": "Hi",
            "preview": "Hi",
            "received_at": account.created_at,
        },
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/email/inbox?unread=true")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_ai_summary_returns_non_empty():
    store = get_email_store()
    account = await store.create_account(
        "local",
        {
            "email_address": "a@b.com",
            "imap_host": "i",
            "smtp_host": "s",
            "username": "a@b.com",
            "password": "x",
        },
    )
    email = await store.upsert_email(
        account,
        {
            "message_id": "m2",
            "uid": 2,
            "folder": "INBOX",
            "from_address": "boss@example.com",
            "to_addresses": ["a@b.com"],
            "subject": "Urgent deadline",
            "body_text": "Please respond ASAP",
            "preview": "Please respond ASAP",
            "received_at": account.created_at,
        },
    )
    assert email is not None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/email/{email.id}/ai-summary")
    assert response.status_code == 200
    assert response.json()["summary"]


@pytest.mark.asyncio
async def test_send_email_calls_smtp():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/email/accounts",
            json={
                "email_address": "user@example.com",
                "imap_host": "imap.example.com",
                "smtp_host": "smtp.example.com",
                "username": "user@example.com",
                "password": "secret",
            },
        )
        assert created.status_code == 201
        with patch("keprix.email.routes.send_smtp_message") as send_mock:
            response = await client.post(
                "/api/email/send",
                json={
                    "to_addresses": ["dest@example.com"],
                    "subject": "Test",
                    "body": "Hello",
                },
            )
    assert response.status_code == 200
    send_mock.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_server_lists_six_tools():
    from keprix.email.mcp_server import _tools

    tools = _tools()
    names = {t.name for t in tools}
    assert len(names) >= 6
    assert "list_emails" in names
    assert "send_email" in names
