"""Tests for developer identity bootstrap."""

from __future__ import annotations

import json
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from keprix.keys.developer_identity import (
    create_developer_identity,
    installation_fingerprint,
    revoke_developer_identity,
    verify_developer_identity,
)
from keprix.keys.local_access import effective_access_level


@pytest.fixture
def identity_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    identity_dir = tmp_path / "identity"
    config_dir = tmp_path / "config"
    monkeypatch.setattr("keprix.keys.developer_identity.DEVELOPER_IDENTITY_DIR", str(identity_dir))
    monkeypatch.setattr("keprix.keys.developer_identity.DEVELOPER_CONFIG_DIR", str(config_dir))
    return identity_dir, config_dir


def test_create_developer_identity_writes_secure_files(identity_home):
    identity_dir, config_dir = identity_home
    status = create_developer_identity()
    assert status["valid"] is True
    for name in ("developer.key", "developer.pub", "dev.json"):
        path = identity_dir / name
        assert path.is_file()
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    config_env = config_dir / "config.env"
    assert "KEPRIX_DEVELOPER_MODE=true" in config_env.read_text(encoding="utf-8")


def test_verify_developer_identity_true_on_same_machine(identity_home):
    create_developer_identity()
    assert verify_developer_identity() is True
    assert effective_access_level() == "developer"


def test_verify_developer_identity_false_after_tamper(identity_home):
    identity_dir, _ = identity_home
    create_developer_identity()
    dev_json = identity_dir / "dev.json"
    record = json.loads(dev_json.read_text(encoding="utf-8"))
    record["payload"]["installation_fingerprint"] = "tampered"
    dev_json.write_text(json.dumps(record), encoding="utf-8")
    assert verify_developer_identity() is False
    assert effective_access_level() == "standard"


def test_fingerprint_mismatch_on_copied_dev_json(identity_home, monkeypatch):
    identity_dir, _ = identity_home
    create_developer_identity()
    original = json.loads((identity_dir / "dev.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(
        "keprix.keys.developer_identity.installation_fingerprint",
        lambda: "different-machine",
    )
    (identity_dir / "dev.json").write_text(json.dumps(original), encoding="utf-8")
    assert verify_developer_identity() is False


def test_verify_makes_no_http_calls(identity_home):
    create_developer_identity()
    with patch("httpx.request") as mock_request:
        assert verify_developer_identity() is True
    mock_request.assert_not_called()


def test_revoke_removes_identity(identity_home):
    identity_dir, config_dir = identity_home
    create_developer_identity()
    revoke_developer_identity()
    assert not (identity_dir / "dev.json").exists()
    assert "KEPRIX_DEVELOPER_MODE=false" in (config_dir / "config.env").read_text(encoding="utf-8")
    assert verify_developer_identity() is False
