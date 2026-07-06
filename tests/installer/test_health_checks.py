"""Health check table and mock probes."""

from __future__ import annotations

from keprix.installer.health import HealthCheck, all_passed, format_health_table, run_health_checks


def test_health_checks_with_mock_probe(monkeypatch):
    monkeypatch.setattr(
        "keprix.installer.health._command_ok",
        lambda _cmd: (True, "ok"),
    )

    def mock_probe(url: str) -> tuple[bool, str]:
        if "3333" in url or "3000" in url or "8080" in url:
            return True, "HTTP 200"
        return False, "unknown"

    checks = run_health_checks(
        check_fn=mock_probe,
        postgres_host="127.0.0.1",
        redis_host="127.0.0.1",
    )
    names = {check.name for check in checks}
    assert names == {"backend", "frontend", "postgres", "redis", "searxng"}
    backend = next(check for check in checks if check.name == "backend")
    assert backend.ok
    table = format_health_table(checks)
    assert "backend" in table
    assert all_passed(checks)
