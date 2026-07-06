"""Tests for slash command permissions and execution."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.server import create_app
from keprix.slash.audit import SlashAuditStore, redact_args
from keprix.slash.confirmations import SlashConfirmationStore, get_cyber_authorization_store
from keprix.slash.executor import approve_token, build_context, execute_context
from keprix.slash.registry import SlashRegistry
from keprix.slash.schemas import SlashCommand, SlashContext, SlashResult


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
def audit_store(tmp_path, monkeypatch):
    store = SlashAuditStore(base_dir=tmp_path / "slash")
    monkeypatch.setattr("keprix.slash.audit.get_slash_audit_store", lambda: store)
    monkeypatch.setattr("keprix.slash.executor.get_slash_audit_store", lambda: store)
    monkeypatch.setattr("keprix.slash.routes.get_slash_audit_store", lambda: store)
    return store


@pytest.fixture
def confirm_store(tmp_path, monkeypatch):
    store = SlashConfirmationStore(ttl_seconds=600)
    monkeypatch.setattr("keprix.slash.confirmations.get_confirmation_store", lambda: store)
    monkeypatch.setattr("keprix.slash.executor.get_confirmation_store", lambda: store)
    return store


@pytest.mark.asyncio
async def test_help_lists_role_commands(audit_store):
    ctx = build_context(
        raw_text="/help",
        user_id="u1",
        workspace_id="ws1",
        channel="cli",
        channel_user_id="u1",
        role="viewer",
    )
    result = await execute_context(ctx)
    assert result.ok is True
    assert "/help" in result.message
    assert "/status" in result.message
    assert result.audit_id


@pytest.mark.asyncio
async def test_viewer_cannot_run_admin_command(audit_store):
    ctx = build_context(
        raw_text="/diagnostics",
        user_id="u1",
        workspace_id="ws1",
        channel="webchat",
        channel_user_id="u1",
        role="viewer",
    )
    result = await execute_context(ctx)
    assert result.ok is False
    assert "Permission denied" in result.message


@pytest.mark.asyncio
async def test_risky_command_returns_confirmation(audit_store, confirm_store):
    ctx = build_context(
        raw_text='/memory save "remember this"',
        user_id="u1",
        workspace_id="ws1",
        channel="cli",
        channel_user_id="u1",
        role="operator",
    )
    result = await execute_context(ctx)
    assert result.requires_confirmation is True
    assert result.confirmation_token


@pytest.mark.asyncio
async def test_approval_executes_once(audit_store, confirm_store, monkeypatch):
    saved = {"count": 0}

    async def fake_save(ctx: SlashContext, data: dict) -> SlashResult:
        saved["count"] += 1
        return SlashResult(ok=True, message="saved")

    monkeypatch.setattr("keprix.slash.executor._execute_confirmed_action", fake_save)

    ctx = build_context(
        raw_text='/memory save "hello"',
        user_id="u1",
        workspace_id="ws1",
        channel="cli",
        channel_user_id="u1",
        role="operator",
    )
    pending = await execute_context(ctx)
    token = pending.confirmation_token
    assert token

    approve_ctx = build_context(
        raw_text=f"/approve {token}",
        user_id="u1",
        workspace_id="ws1",
        channel="cli",
        channel_user_id="u1",
        role="operator",
        confirmation_token=token,
    )
    approved = await approve_token(approve_ctx, token)
    assert approved.ok is True
    assert saved["count"] == 1

    again = await approve_token(approve_ctx, token)
    assert again.ok is False


@pytest.mark.asyncio
async def test_expired_token_fails(audit_store, confirm_store):
    token, token_hash = confirm_store.create(
        command="memory.save",
        context={"data": {"action": "memory.save", "content": "x"}},
        user_id="u1",
        workspace_id="ws1",
        role="operator",
        preview="save",
        risk_level="medium",
    )
    pending = confirm_store.get(token)
    assert pending is not None
    pending.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    ctx = build_context(
        raw_text=f"/approve {token}",
        user_id="u1",
        workspace_id="ws1",
        channel="cli",
        channel_user_id="u1",
        role="operator",
    )
    result = await approve_token(ctx, token)
    assert result.ok is False


def test_audit_redacts_secrets():
    payload = {"api_key": "sk-abcdefghijklmnop", "note": "safe"}
    redacted = redact_args(payload)
    assert "[REDACTED]" in redacted["api_key"] or "sk-" not in redacted["api_key"]


@pytest.mark.asyncio
async def test_cyber_command_blocked_without_authorization(audit_store, monkeypatch):
    registry = SlashRegistry()

    async def handler(_ctx: SlashContext) -> SlashResult:
        return SlashResult(ok=True, message="cyber")

    registry.register(
        SlashCommand(
            name="cyber.scan",
            description="cyber",
            min_role="owner",
            cyber_scoped=True,
            handler=handler,
        )
    )
    monkeypatch.setattr("keprix.slash.executor.get_slash_registry", lambda: registry)
    monkeypatch.setattr("keprix.slash.registry.get_slash_registry", lambda: registry)

    ctx = build_context(
        raw_text="/cyber scan",
        user_id="u1",
        workspace_id="ws1",
        channel="cli",
        channel_user_id="u1",
        role="owner",
    )
    result = await execute_context(ctx)
    assert result.ok is False
    assert "authorization" in result.message.lower()


@pytest.mark.asyncio
async def test_api_execute_status(client, audit_store):
    response = await client.post(
        "/api/slash/execute",
        headers={"X-Slash-Role": "admin"},
        json={"text": "/status", "channel": "webchat", "user_id": "u1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "Keprix" in payload["message"]


@pytest.mark.asyncio
async def test_research_confirmation_starts_job(audit_store, confirm_store, monkeypatch):
    scheduled: list[str] = []

    def fake_schedule(job) -> None:
        scheduled.append(job.id)

    monkeypatch.setattr("keprix.research.pipeline.schedule_research_job", fake_schedule)

    ctx = build_context(
        raw_text='/research "market map" --depth standard',
        user_id="u1",
        workspace_id="ws1",
        channel="cli",
        channel_user_id="u1",
        role="operator",
    )
    pending = await execute_context(ctx)
    assert pending.requires_confirmation is True
    token = pending.confirmation_token
    assert token

    approved = await approve_token(
        build_context(
            raw_text=f"/approve {token}",
            user_id="u1",
            workspace_id="ws1",
            channel="cli",
            channel_user_id="u1",
            role="operator",
            confirmation_token=token,
        ),
        token,
    )
    assert approved.ok is True
    assert "Research job" in approved.message
    assert len(scheduled) == 1
