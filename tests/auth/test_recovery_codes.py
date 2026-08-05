"""Tests for TOTP recovery codes."""

from __future__ import annotations

import pyotp
import pytest

from keprix.auth.session import AuthManager


@pytest.fixture
def auth_manager(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    manager = AuthManager(str(tmp_path / "auth.json"))
    manager.create_user("alice", "alice-pass", email="alice@example.com", role="user")
    return manager


def _enable_totp(auth: AuthManager, username: str) -> str:
    secret, _uri = auth.totp_setup(username)
    code = pyotp.TOTP(secret).now()
    assert auth.totp_confirm(username, code) is True
    return secret


def test_generate_and_consume_recovery_code_once(auth_manager):
    _enable_totp(auth_manager, "alice")
    codes = auth_manager.generate_recovery_codes("alice")
    assert len(codes) == 10
    assert "-" in codes[0]

    assert auth_manager.consume_recovery_code("alice", codes[0]) is True
    assert auth_manager.consume_recovery_code("alice", codes[0]) is False


def test_regenerate_invalidates_previous_codes(auth_manager):
    _enable_totp(auth_manager, "alice")
    first = auth_manager.generate_recovery_codes("alice")
    second = auth_manager.generate_recovery_codes("alice")
    assert first[0] != second[0]
    assert auth_manager.consume_recovery_code("alice", first[0]) is False
    assert auth_manager.consume_recovery_code("alice", second[0]) is True


def test_generate_requires_totp_enabled(auth_manager):
    with pytest.raises(ValueError, match="not enabled"):
        auth_manager.generate_recovery_codes("alice")
