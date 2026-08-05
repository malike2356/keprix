"""Tests for security/egress_audit.py."""

from __future__ import annotations

import json

import pytest

from keprix.security.egress_audit import EgressAuditLog


@pytest.fixture
def audit(tmp_path):
    return EgressAuditLog(log_dir=tmp_path / "egress")


@pytest.mark.asyncio
async def test_log_allow_writes_allowed_entry(audit, tmp_path):
    await audit.log_allow("aiva", "api.sendgrid.com", "167.89.0.1",
                          "https://api.sendgrid.com/v3/stats", "host_in_allowlist")
    audit.close()

    log_files = list((tmp_path / "egress").glob("*.ndjson"))
    assert len(log_files) == 1
    entry = json.loads(log_files[0].read_text().strip())
    assert entry["decision"] == "ALLOWED"
    assert entry["host"] == "api.sendgrid.com"
    assert entry["ip"] == "167.89.0.1"
    assert entry["reason"] == "host_in_allowlist"


@pytest.mark.asyncio
async def test_log_block_writes_blocked_entry(audit, tmp_path):
    await audit.log_block("aiva", "192.168.1.1", "192.168.1.1",
                          "https://192.168.1.1/api", "private_ip_blocked")
    audit.close()

    log_files = list((tmp_path / "egress").glob("*.ndjson"))
    entry = json.loads(log_files[0].read_text().strip())
    assert entry["decision"] == "BLOCKED"
    assert entry["reason"] == "private_ip_blocked"


@pytest.mark.asyncio
async def test_multiple_entries(audit, tmp_path):
    await audit.log_allow("aiva", "api.stripe.com", "54.1.1.1", "/charge", "host_in_allowlist")
    await audit.log_block("abbis", "evil.com", "5.5.5.5", "/steal", "host_not_in_allowlist")
    audit.close()

    log_files = list((tmp_path / "egress").glob("*.ndjson"))
    lines = [l for l in log_files[0].read_text().splitlines() if l.strip()]
    assert len(lines) == 2


@pytest.mark.asyncio
async def test_tail_returns_last_n(audit):
    for i in range(5):
        await audit.log_allow("aiva", f"host{i}.com", "1.1.1.1", f"/path{i}", "host_in_allowlist")
    audit.close()

    entries = audit.tail(3)
    assert len(entries) == 3
    assert entries[-1]["host"] == "host4.com"


def test_tail_empty_log(tmp_path):
    log = EgressAuditLog(log_dir=tmp_path / "no_log")
    assert log.tail() == []


@pytest.mark.asyncio
async def test_session_and_tool_logged(audit, tmp_path):
    await audit.log_block("aiva", "10.0.0.1", "10.0.0.1", "/private",
                          "private_ip_blocked", session_id="sess-abc", tool_name="web_search")
    audit.close()

    log_files = list((tmp_path / "egress").glob("*.ndjson"))
    entry = json.loads(log_files[0].read_text().strip())
    assert entry["session_id"] == "sess-abc"
    assert entry["tool_name"] == "web_search"


@pytest.mark.asyncio
async def test_entry_has_timestamp(audit, tmp_path):
    await audit.log_allow("aiva", "api.stripe.com", "54.1.1.1", "/", "host_in_allowlist")
    audit.close()
    log_files = list((tmp_path / "egress").glob("*.ndjson"))
    entry = json.loads(log_files[0].read_text().strip())
    assert "ts" in entry
    assert isinstance(entry["ts"], float)
