"""First-run owner mint is not gated by KEPRIX_MULTI_USER."""

from __future__ import annotations

from keprix.auth.session import AuthManager


def test_bootstrap_owner_works_when_multi_user_is_off(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_MULTI_USER", "false")
    monkeypatch.delenv("KEPRIX_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("KEPRIX_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    auth = AuthManager(str(tmp_path / "auth.json"))

    blocked, message = auth.register("other", "xxxxxxxx")
    assert blocked is False
    assert message == "Registration disabled"

    ok, created = auth.bootstrap_owner(
        "owner@example.com",
        "solo-pass-1",
        display_name="Laud Paul",
    )
    assert ok is True
    owner = auth.get_user("owner@example.com")
    assert owner is not None
    assert owner["role"] == "admin"
    assert owner["display_name"] == "Laud Paul"

    token, user, error = auth.login("owner@example.com", "solo-pass-1")
    assert error is None
    assert token
    assert user["username"] == "owner@example.com"


def test_bootstrap_owner_retargets_env_admin_placeholder(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_MULTI_USER", "false")
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_ADMIN_EMAIL", "")
    monkeypatch.setenv("ADMIN_EMAIL", "")
    auth = AuthManager(str(tmp_path / "auth.json"))
    assert auth.get_user("admin") is not None

    ok, _message = auth.bootstrap_owner("owner@example.com", "wizard-pass-1", display_name="Owner")
    assert ok is True
    assert auth.get_user("admin") is None
    owner = auth.get_user("owner@example.com")
    assert owner is not None
    assert owner["display_name"] == "Owner"

    token, _user, error = auth.login("owner@example.com", "wizard-pass-1")
    assert error is None
    assert token
