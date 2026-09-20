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


def test_postgres_not_used_without_explicit_url(monkeypatch):
    from keprix.db.email_repo import postgres_configured, _use_db

    monkeypatch.delenv("KEPRIX_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert postgres_configured() is False
    modules = {key: value for key, value in __import__("sys").modules.items() if key != "pytest"}
    monkeypatch.setattr("keprix.db.email_repo.sys.modules", modules)
    assert _use_db() is False


def test_create_and_list_accounts_without_postgres(tmp_path, monkeypatch):
    import asyncio

    monkeypatch.delenv("KEPRIX_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    reset_email_store()
    store = get_email_store()

    created = asyncio.run(
        store.create_account(
            "u-local",
            {
                "label": "Gmail",
                "email_address": "me@gmail.com",
                "imap_host": "imap.gmail.com",
                "smtp_host": "smtp.gmail.com",
                "username": "me@gmail.com",
                "password": "app-password",
            },
        )
    )
    listed = asyncio.run(store.list_accounts("u-local"))
    assert created.email_address == "me@gmail.com"
    assert [row.id for row in listed] == [created.id]
    assert (tmp_path / "workspace" / "email_store.json").exists()

    reset_email_store()
    restored = asyncio.run(get_email_store().list_accounts("u-local"))
    assert [row.email_address for row in restored] == ["me@gmail.com"]


def test_pg_list_accounts_returns_none_on_connect_error(monkeypatch):
    import asyncio

    from keprix.db import email_repo

    monkeypatch.setattr(email_repo, "_use_db", lambda: True)

    class Boom:
        def __call__(self):
            return self

        async def __aenter__(self):
            raise OSError("Connect call failed ('127.0.0.1', 5432)")

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr(email_repo, "get_session_factory", lambda: Boom)
    assert asyncio.run(email_repo.pg_list_accounts("u1")) is None


def test_sync_reports_imap_failure(monkeypatch):
    import asyncio

    from keprix.email.pollers import sync_all_accounts
    from keprix.email.store import EmailAccountRecord, _utcnow

    account = EmailAccountRecord(
        id="acc-1",
        user_id="u1",
        label="Gmail",
        email_address="me@gmail.com",
        imap_host="imap.gmail.com",
        imap_port=993,
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        username="me@gmail.com",
        password_encrypted="",
        use_tls=True,
        use_starttls=True,
        poll_interval_seconds=300,
        last_polled_at=None,
        is_active=True,
        created_at=_utcnow(),
    )

    class Store:
        async def list_active_accounts(self):
            return [account]

    monkeypatch.setattr("keprix.email.pollers.get_email_store", lambda: Store())

    async def boom(_account, *, raise_on_error=False):
        if raise_on_error:
            raise RuntimeError("AUTHENTICATIONFAILED")
        return 0

    monkeypatch.setattr("keprix.email.pollers._poll_account", boom)
    result = asyncio.run(sync_all_accounts("u1"))
    assert result["errors"] == 1
    assert result["synced"] == 0
    assert "AUTHENTICATIONFAILED" in str(result["detail"])
