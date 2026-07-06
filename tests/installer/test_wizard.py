"""Wizard generates valid .env and optional developer identity."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.installer.wizard import WizardAnswers, run_wizard, validate_env_file


@pytest.fixture
def wizard_env(tmp_path, monkeypatch):
    install_home = tmp_path / "install"
    install_home.mkdir()
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "BACKEND_PORT=3333\nFRONTEND_PORT=3000\nKEPRIX_DEFAULT_PROVIDER=auto\n",
        encoding="utf-8",
    )
    env_out = tmp_path / ".env"
    monkeypatch.setenv("KEPRIX_INSTALL_HOME", str(install_home))
    monkeypatch.setenv("KEPRIX_ENV_FILE", str(env_out))
    return env_out, env_example, install_home


def test_wizard_generates_required_env(wizard_env):
    env_out, env_example, install_home = wizard_env
    identity_calls: list[bool] = []

    def fake_identity(*, force: bool = False):
        identity_calls.append(force)
        return {"valid": True, "identity_dir": str(install_home / "identity")}

    result = run_wizard(
        answers=WizardAnswers(is_developer_owner=True, instance_name="lab"),
        interactive=False,
        env_out=env_out,
        env_example=env_example,
        create_developer_identity=fake_identity,
    )
    assert result.env_path.exists()
    assert result.admin_password
    assert result.values["KEPRIX_INSTANCE_NAME"] == "lab"
    missing = validate_env_file(env_out)
    assert missing == []
    assert identity_calls == [False]


def test_wizard_skips_identity_when_not_owner(wizard_env):
    env_out, env_example, _install_home = wizard_env

    def should_not_run(*, force: bool = False):
        raise AssertionError("identity should not be created")

    result = run_wizard(
        answers=WizardAnswers(is_developer_owner=False),
        interactive=False,
        env_out=env_out,
        env_example=env_example,
        create_developer_identity=should_not_run,
    )
    assert result.developer_identity_created is False
    assert validate_env_file(env_out) == []
