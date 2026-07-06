"""Prompt 56 database adapter tests."""

from __future__ import annotations

import pytest

from keprix.backend.tools.adapters.registry import run_adapter


@pytest.mark.asyncio
async def test_database_adapter_read_only_select(monkeypatch):
    monkeypatch.setenv("MYSQL_READONLY_URL", "mysql://readonly@localhost/db")
    result = await run_adapter("mysql", "query", {"sql": "SELECT id FROM users"}, dry_run=False)
    assert result.ok is True
    assert result.data["read_only"] is True


@pytest.mark.asyncio
async def test_database_adapter_blocks_write_without_approval(monkeypatch):
    monkeypatch.setenv("MYSQL_READONLY_URL", "mysql://readonly@localhost/db")
    result = await run_adapter(
        "mysql",
        "write",
        {"sql": "INSERT INTO users VALUES (1)"},
        dry_run=False,
        approved=False,
    )
    assert result.ok is False
    assert "approval" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_automation_adapter_dry_run_by_default(monkeypatch):
    monkeypatch.setenv("ZAPIER_WEBHOOK_URL", "https://hooks.zapier.com/test")
    result = await run_adapter("zapier", "invoke", {"action": "send_email"}, dry_run=True)
    assert result.ok is True
    assert result.dry_run is True
