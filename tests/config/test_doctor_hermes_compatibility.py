from __future__ import annotations

from pathlib import Path


def test_doctor_reports_legacy_hermes_compatibility_without_secrets(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    from keprix.keprix_cli import doctor

    legacy_home = tmp_path / ".hermes"
    legacy_home.mkdir()
    (legacy_home / ".env").write_text("HERMES_SAMPLE_TOKEN=secret-value\n", encoding="utf-8")
    (legacy_home / "config.yaml").write_text("model:\n  default: legacy\n", encoding="utf-8")

    monkeypatch.setenv("HERMES_HOME", str(legacy_home))
    monkeypatch.setenv("HERMES_SHELL_TOKEN", "shell-secret")
    monkeypatch.delenv("KEPRIX_HOME", raising=False)

    doctor._check_hermes_compatibility()

    output = capsys.readouterr().out
    assert "Legacy Hermes state directory detected" in output
    assert "HERMES_SAMPLE_TOKEN" in output
    assert "HERMES_SHELL_TOKEN" in output
    assert "secret-value" not in output
    assert "shell-secret" not in output
