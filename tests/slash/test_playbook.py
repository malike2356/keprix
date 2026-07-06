"""Tests for playbook slash integration."""

from __future__ import annotations

import pytest

from keprix.slash.executor import build_context, execute_context
from keprix.slash.audit import SlashAuditStore


@pytest.fixture
def audit_store(tmp_path, monkeypatch):
    store = SlashAuditStore(base_dir=tmp_path / "slash")
    monkeypatch.setattr("keprix.slash.audit.get_slash_audit_store", lambda: store)
    monkeypatch.setattr("keprix.slash.executor.get_slash_audit_store", lambda: store)
    return store


@pytest.mark.asyncio
async def test_playbook_scan_calls_hwfit(audit_store, monkeypatch):
    monkeypatch.setattr(
        "keprix.playbook.hwfit.scan_hardware",
        lambda: {"cpu": "test", "ram_gb": 16},
    )

    ctx = build_context(
        raw_text="/playbook scan",
        user_id="u1",
        workspace_id="ws1",
        channel="cli",
        channel_user_id="u1",
        role="admin",
    )
    result = await execute_context(ctx)
    assert result.ok is True
    assert "hardware" in result.data
