"""Installer telemetry tests."""

from __future__ import annotations

import os

from keprix.installer.telemetry import build_telemetry_payload, record_telemetry


def test_telemetry_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("KEPRIX_INSTALL_TELEMETRY", raising=False)
    assert record_telemetry("install_complete", success=True) is None


def test_telemetry_payload_shape(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_INSTALL_TELEMETRY", "true")
    payload = build_telemetry_payload("step_complete", step="preflight", success=True)
    assert payload["event"] == "step_complete"
    assert "install_id" in payload
