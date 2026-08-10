"""Session policy and concurrent/revocation tests."""

from __future__ import annotations

import time

from keprix.auth.session import AuthManager, ConcurrentSessionLimitError
from keprix.sessions import (
    clear_session_policy_state_for_tests,
    get_revocation_log,
    resolve_session_config,
    set_max_concurrent,
)


def test_idle_and_absolute_and_concurrent_then_password_revoke(tmp_path, monkeypatch):
    clear_session_policy_state_for_tests()
    monkeypatch.setenv("KEPRIX_SESSION_TIER", "content")
    monkeypatch.setenv("SESSION_IDLE_TIMEOUT_MS", "60000")
    monkeypatch.setenv("SESSION_ABSOLUTE_MAX_MS", "120000")
    monkeypatch.setenv("SESSION_MAX_CONCURRENT", "5")
    set_max_concurrent("keprix", 5)

    auth = AuthManager(auth_path=str(tmp_path / "auth.json"))
    auth._config["users"] = {
        "alice": {
            "id": "u-alice",
            "username": "alice",
            "email": "alice@example.com",
            "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G2oQ.placeholder",
            "role": "user",
            "is_approved": True,
            "is_active": True,
        }
    }
    # bypass password: create sessions directly
    tokens = []
    for i in range(6):
        tok = auth.create_session(
            "alice",
            device_label=f"Chrome on Windows {i}",
            ip_address=f"10.0.0.{i+1}",
            user_agent=f"Mozilla Chrome/{100+i} Windows",
            location="Berlin, DE" if i == 0 else f"City-{i}",
        )
        tokens.append(tok)
    assert len(auth._sessions) == 5
    assert get_revocation_log(user_id="u-alice")

    # absolute expiry
    for meta in auth._sessions.values():
        meta["expiry"] = time.time() - 1
    auth._save_sessions()
    assert auth.validate_token(tokens[-1]) is None

    # recreate and revoke all on password change
    tokens = []
    for i in range(3):
        tokens.append(auth.create_session("alice", device_label=f"Dev {i}", ip_address=f"1.1.1.{i}"))
    removed = auth.revoke_all_user_sessions("u-alice", reason="password_changed")
    assert removed == 3
    assert auth.validate_token(tokens[0]) is None
    assert any(r["reason"] == "password_changed" for r in get_revocation_log(user_id="u-alice"))


def test_block_new_policy(tmp_path, monkeypatch):
    clear_session_policy_state_for_tests()
    monkeypatch.setenv("SESSION_ON_LIMIT", "block_new")
    monkeypatch.setenv("SESSION_MAX_CONCURRENT", "2")
    auth = AuthManager(auth_path=str(tmp_path / "auth.json"))
    auth._config["users"] = {
        "bob": {
            "id": "u-bob",
            "username": "bob",
            "password_hash": "x",
            "role": "user",
            "is_approved": True,
            "is_active": True,
        }
    }
    auth.create_session("bob", device_label="A", ip_address="1.1.1.1")
    auth.create_session("bob", device_label="B", ip_address="1.1.1.2")
    try:
        auth.create_session("bob", device_label="C", ip_address="1.1.1.3")
        raised = False
    except ConcurrentSessionLimitError:
        raised = True
    assert raised is True
    assert resolve_session_config()["on_limit"] == "block_new"
