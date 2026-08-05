"""Credential audit trail tests."""

from __future__ import annotations

from keprix.tools.credential_audit import list_credential_audits, record_credential_audit


def test_credential_audit_records_401_rotation_link(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))

    record_credential_audit(
        tool="google_calendar.create",
        route={"host": "www.googleapis.com", "path": "/calendar/v3/events", "method": "POST"},
        credential_ref="google-api-key",
        status="unauthorized",
        duration_ms=312,
        response_status=401,
        session_id="sess_abc123",
    )

    rows = list_credential_audits()

    assert rows[0]["tool"] == "google_calendar.create"
    assert rows[0]["response_status"] == 401
    assert rows[0]["rotation_docs_url"]
    assert "google-api-key" in rows[0]["credential_ref"]
