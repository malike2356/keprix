"""Installer preflight tests."""

from __future__ import annotations

from keprix.installer.preflight import run_preflight


def test_preflight_runs_checks() -> None:
    report = run_preflight(ports=[59999])
    assert report.checks
    assert any(check.name == "python_version" for check in report.checks)
