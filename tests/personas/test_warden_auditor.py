"""Tests for WARDEN auditor module."""

from __future__ import annotations

import pytest

from keprix.personas.warden.auditor import Severity, WardenAuditor
from keprix.security.crypto import decrypt_text, derive_key


@pytest.fixture
def auditor() -> WardenAuditor:
    return WardenAuditor(workspace_id="ws-warden")


def test_audit_finds_debug_mode(auditor: WardenAuditor) -> None:
    report = auditor.run_audit(config={"debug": True})
    assert any(f.rule == "debug_disabled" for f in report.findings)
    assert report.findings[0].severity == Severity.HIGH


def test_audit_detects_secrets(auditor: WardenAuditor) -> None:
    report = auditor.run_audit(content_samples=['API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"'])
    assert any(f.category == "secrets" for f in report.findings)
    assert any(f.severity == Severity.CRITICAL for f in report.findings)


def test_audit_flags_unpinned_dependencies(auditor: WardenAuditor) -> None:
    report = auditor.run_audit(requirements=["requests", "pillow"])
    rules = {f.rule for f in report.findings}
    assert "unpinned_dependency" in rules


def test_out_of_scope_pentest_refused(auditor: WardenAuditor) -> None:
    report = auditor.run_audit(request="Run a penetration test on our API")
    assert report.out_of_scope
    assert any(f.rule == "out_of_scope" for f in report.findings)


def test_out_of_scope_osint_refused(auditor: WardenAuditor) -> None:
    assert auditor.is_out_of_scope("Perform OSINT reconnaissance on competitors")


def test_encrypt_report_round_trip(auditor: WardenAuditor) -> None:
    report = auditor.run_audit(config={"debug": True})
    stored = auditor.encrypt_report(report, encryption_key="test-workspace-key")
    assert stored["algorithm"] == "AES-256-GCM"
    assert stored["encrypted"]

    key = derive_key("test-workspace-key", salt=b"warden-audit-v1")
    decrypted = decrypt_text(stored["encrypted"], key)
    assert report.audit_id in decrypted


def test_run_audit_stores_encrypted_report_by_default(auditor: WardenAuditor) -> None:
    report = auditor.run_audit(config={"debug": True})
    assert report.encrypted_storage is not None
    assert report.encrypted_storage["algorithm"] == "AES-256-GCM"


def test_incident_report_renders(auditor: WardenAuditor) -> None:
    report = auditor.run_audit(config={"debug": True})
    markdown = auditor.render_incident_report(
        incident_id="INC-001",
        severity="High",
        summary="Debug mode enabled in production",
        findings=report.findings,
    )
    assert "INC-001" in markdown
    assert "Debug mode" in markdown


@pytest.mark.asyncio
async def test_audit_playbook_completes(auditor: WardenAuditor) -> None:
    result = await auditor.run_audit_playbook({"config": {"debug": True}})
    assert result["status"] == "completed"
    assert result["audit_summary"]["total"] >= 1
