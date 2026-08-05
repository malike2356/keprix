"""Tests for security/tool_acl_audit.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.security.tool_acl import ACLDecision
from keprix.security.tool_acl_audit import ToolACLAuditLog


@pytest.fixture
def audit_log(tmp_path):
    return ToolACLAuditLog(log_dir=tmp_path / "tool_acl")


@pytest.mark.asyncio
async def test_record_writes_ndjson(audit_log, tmp_path):
    await audit_log.record("aiva", "crm:list", ACLDecision.ALLOWED, workspace_id="ws-1")
    audit_log.close()

    log_files = list((tmp_path / "tool_acl").glob("*.ndjson"))
    assert len(log_files) == 1

    line = log_files[0].read_text().strip()
    entry = json.loads(line)
    assert entry["product_id"] == "aiva"
    assert entry["tool_name"] == "crm:list"
    assert entry["decision"] == "allowed"
    assert entry["workspace_id"] == "ws-1"


@pytest.mark.asyncio
async def test_record_denial(audit_log, tmp_path):
    await audit_log.record("aiva", "terminal:run", ACLDecision.DENIED)
    audit_log.close()

    log_files = list((tmp_path / "tool_acl").glob("*.ndjson"))
    entry = json.loads(log_files[0].read_text().strip())
    assert entry["decision"] == "denied"


@pytest.mark.asyncio
async def test_record_multiple_entries(audit_log, tmp_path):
    await audit_log.record("aiva", "crm:list", ACLDecision.ALLOWED)
    await audit_log.record("abbis", "terminal:run", ACLDecision.DENIED_NOT_LISTED)
    await audit_log.record("aiva", "email:send", ACLDecision.ALLOWED)
    audit_log.close()

    log_files = list((tmp_path / "tool_acl").glob("*.ndjson"))
    lines = [l for l in log_files[0].read_text().splitlines() if l.strip()]
    assert len(lines) == 3


@pytest.mark.asyncio
async def test_tail_returns_last_n(audit_log, tmp_path):
    for i in range(5):
        await audit_log.record("aiva", f"tool:{i}", ACLDecision.ALLOWED)
    audit_log.close()

    entries = audit_log.tail(3)
    assert len(entries) == 3
    assert entries[-1]["tool_name"] == "tool:4"


@pytest.mark.asyncio
async def test_tail_with_empty_log(tmp_path):
    log = ToolACLAuditLog(log_dir=tmp_path / "empty_acl")
    entries = log.tail(10)
    assert entries == []


@pytest.mark.asyncio
async def test_entry_has_timestamp(audit_log, tmp_path):
    await audit_log.record("aiva", "crm:list", ACLDecision.ALLOWED)
    audit_log.close()
    log_files = list((tmp_path / "tool_acl").glob("*.ndjson"))
    entry = json.loads(log_files[0].read_text().strip())
    assert "ts" in entry
    assert isinstance(entry["ts"], float)
    assert entry["ts"] > 0


@pytest.mark.asyncio
async def test_session_id_included(audit_log, tmp_path):
    await audit_log.record(
        "aiva", "crm:list", ACLDecision.ALLOWED,
        workspace_id="ws-1", session_id="sess-abc"
    )
    audit_log.close()
    log_files = list((tmp_path / "tool_acl").glob("*.ndjson"))
    entry = json.loads(log_files[0].read_text().strip())
    assert entry["session_id"] == "sess-abc"
