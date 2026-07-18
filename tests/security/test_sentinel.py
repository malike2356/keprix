"""Tests for Scout Sentinel client and auto_response escalation."""

from __future__ import annotations

import json
import socket
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from keprix.security.auto_response import (
    evaluate_signal,
    reset_auto_response_state,
)
from keprix.security.scout_control import (
    egress_force_blocked,
    is_session_blocked,
    reset_scout_control,
)
from keprix.security.sentinel_client import (
    ensure_sentinel_health,
    sentinel_available,
    sentinel_block_egress,
    sentinel_health_check,
)


@pytest.fixture(autouse=True)
def _reset(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("SENTINEL_REQUIRED", raising=False)
    monkeypatch.delenv("SENTINEL_ALLOW_KILL", raising=False)
    monkeypatch.delenv("SENTINEL_ENFORCE", raising=False)
    reset_scout_control()
    reset_auto_response_state()
    yield
    reset_scout_control()
    reset_auto_response_state()


def test_client_returns_error_when_socket_absent(tmp_path, monkeypatch):
    missing = tmp_path / "no-such.sock"
    monkeypatch.setenv("SENTINEL_SOCKET", str(missing))
    assert sentinel_available() is False
    assert sentinel_block_egress() is False
    resp = sentinel_health_check()
    assert resp["status"] == "error"
    assert "sentinel not running" in resp["reason"]


def test_client_ok_when_socket_present(tmp_path, monkeypatch):
    sock_path = tmp_path / "sentinel.sock"

    def _serve() -> None:
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if sock_path.exists():
            sock_path.unlink()
        server.bind(str(sock_path))
        server.listen(1)
        conn, _ = server.accept()
        try:
            data = conn.recv(65536)
            cmd = json.loads(data.decode("utf-8"))
            if cmd.get("action") == "health_check":
                payload = {"status": "ok", "healthy": True, "egress_blocked": False}
            else:
                payload = {"status": "ok", "action": cmd.get("action"), "dry_run": True}
            conn.sendall(json.dumps(payload).encode("utf-8"))
        finally:
            conn.close()
            server.close()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    # Wait briefly for bind
    for _ in range(50):
        if sock_path.exists():
            break
        import time

        time.sleep(0.01)

    monkeypatch.setenv("SENTINEL_SOCKET", str(sock_path))
    assert sentinel_available() is True
    assert sentinel_health_check().get("status") == "ok"
    thread.join(timeout=2)


def test_auto_response_works_without_sentinel(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_SOCKET", str(tmp_path / "absent.sock"))
    response = None
    for _ in range(3):
        response = evaluate_signal(
            session_id="sess-auto",
            product_id="fleet_z",
            severity="critical",
            action="injection_detected",
        )
    assert response is not None
    assert response["severity"] == "CRITICAL"
    assert is_session_blocked("sess-auto") is True


def test_auto_response_l4_calls_sentinel_when_socket_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_SOCKET", str(tmp_path / "sentinel.sock"))
    Path(tmp_path / "sentinel.sock").touch()

    with (
        patch("keprix.security.auto_response.sentinel_block_egress", return_value=True) as block,
        patch(
            "keprix.security.auto_response.sentinel_protect_files", return_value=True
        ) as protect,
        patch("keprix.security.auto_response.sentinel_available", return_value=True),
    ):
        responses = []
        for _ in range(8):
            responses.append(
                evaluate_signal(
                    session_id="sess-l4",
                    product_id="prod_l4",
                    severity="critical",
                    action="exfil",
                )
            )
        emergencies = [r for r in responses if r and r.get("severity") == "EMERGENCY"]
        assert emergencies, "expected L4 EMERGENCY auto-response"
        assert block.called
        assert protect.called


def test_auto_response_l3_skips_kill_by_default(tmp_path, monkeypatch):
    Path(tmp_path / "sentinel.sock").touch()
    monkeypatch.setenv("SENTINEL_SOCKET", str(tmp_path / "sentinel.sock"))
    monkeypatch.delenv("SENTINEL_ALLOW_KILL", raising=False)

    with (
        patch("keprix.security.auto_response.sentinel_available", return_value=True),
        patch("keprix.security.auto_response.sentinel_kill_agent") as kill,
    ):
        response = None
        for _ in range(3):
            response = evaluate_signal(
                session_id="sess-l3",
                product_id="prod_l3",
                severity="critical",
                action="injection",
            )
        assert response is not None
        assert response["severity"] == "CRITICAL"
        assert is_session_blocked("sess-l3") is True
        kill.assert_not_called()


def test_auto_response_l3_kills_when_allow_kill(tmp_path, monkeypatch):
    Path(tmp_path / "sentinel.sock").touch()
    monkeypatch.setenv("SENTINEL_SOCKET", str(tmp_path / "sentinel.sock"))
    monkeypatch.setenv("SENTINEL_ALLOW_KILL", "1")

    with (
        patch("keprix.security.auto_response.sentinel_available", return_value=True),
        patch("keprix.security.auto_response.sentinel_kill_agent", return_value=True) as kill,
    ):
        for _ in range(3):
            evaluate_signal(
                session_id="sess-kill",
                product_id="prod_kill",
                severity="critical",
                action="injection",
            )
        kill.assert_called_once()


def test_ensure_sentinel_health_soft_warn_when_optional(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_SOCKET", str(tmp_path / "missing.sock"))
    monkeypatch.setenv("SENTINEL_REQUIRED", "0")
    result = ensure_sentinel_health()
    assert result["status"] == "error"
    assert egress_force_blocked() is False


def test_ensure_sentinel_health_forces_egress_when_required(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_SOCKET", str(tmp_path / "missing.sock"))
    monkeypatch.setenv("SENTINEL_REQUIRED", "1")
    result = ensure_sentinel_health()
    assert result["status"] == "error"
    assert result.get("fallback") == "egress_force_blocked"
    assert egress_force_blocked() is True


def test_firewall_guard_noop_without_enforce(monkeypatch):
    monkeypatch.delenv("SENTINEL_ENFORCE", raising=False)
    from keprix.security.sentinel.firewall_guard import apply_egress_block

    with patch("keprix.security.sentinel.firewall_guard.subprocess.run") as run:
        result = apply_egress_block()
        assert result["dry_run"] is True
        run.assert_not_called()


def test_file_guard_never_includes_carina_tree():
    from keprix.security.sentinel.file_guard import protected_paths

    paths = protected_paths()
    assert paths
    for path in paths:
        assert "/carina/" not in path
        assert not path.rstrip("/").endswith("carina")
    assert any(p.endswith("scout_control.py") for p in paths)
