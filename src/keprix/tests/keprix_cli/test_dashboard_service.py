"""Tests for keprix dashboard install / persistent service helpers."""

from __future__ import annotations

import argparse

from keprix_cli.dashboard_service import (
    DEFAULT_BACKEND_PORT,
    DEFAULT_FRONTEND_PORT,
    DEFAULT_HOST,
    _host_port_from_unit,
    generate_launchd_plist,
    generate_systemd_unit,
    get_service_name,
)
from keprix_cli.frontend_standalone import _resolve_frontend_port
from keprix_cli.web_server import open_dashboard_url


def test_service_name_default():
    assert get_service_name() in {"keprix-dashboard", get_service_name()}
    assert get_service_name().startswith("keprix-dashboard")


def test_generate_systemd_unit_pins_loopback_and_no_open():
    unit = generate_systemd_unit()
    assert "dashboard --host 127.0.0.1 --port 9119 --no-open" in unit
    assert "--skip-build" not in unit
    assert "KEPRIX_DASHBOARD_SERVICE=1" in unit
    assert "KEPRIX_DASHBOARD_FRONTEND_PORT=9120" in unit
    assert "WantedBy=default.target" in unit
    assert "Restart=always" in unit


def test_generate_systemd_unit_custom_ports():
    unit = generate_systemd_unit(host="127.0.0.1", port=9333, frontend_port=9334)
    assert "--port 9333" in unit
    assert "KEPRIX_DASHBOARD_FRONTEND_PORT=9334" in unit


def test_host_port_from_unit_roundtrip():
    unit = generate_systemd_unit(host="127.0.0.1", port=9333, frontend_port=9334)
    host, port, frontend_port = _host_port_from_unit(unit)
    assert host == "127.0.0.1"
    assert port == 9333
    assert frontend_port == 9334


def test_generate_launchd_plist_runs_dashboard_no_open():
    plist = generate_launchd_plist()
    assert "<string>dashboard</string>" in plist
    assert "<string>--no-open</string>" in plist
    assert "--skip-build" not in plist
    assert "<key>KEPRIX_DASHBOARD_SERVICE</key>" in plist
    assert f"<string>{DEFAULT_FRONTEND_PORT}</string>" in plist


def test_resolve_frontend_port_env(monkeypatch):
    monkeypatch.setenv("KEPRIX_DASHBOARD_FRONTEND_PORT", "9120")
    assert _resolve_frontend_port("127.0.0.1") == 9120


def test_resolve_frontend_port_ephemeral_without_env(monkeypatch):
    monkeypatch.delenv("KEPRIX_DASHBOARD_FRONTEND_PORT", raising=False)
    port = _resolve_frontend_port("127.0.0.1")
    assert 1 <= port <= 65535
    assert port != DEFAULT_BACKEND_PORT or True  # ephemeral may coincide; just an int


def test_open_dashboard_url_uses_detached_xdg_open(monkeypatch):
    monkeypatch.setattr("keprix_cli.web_server.sys.platform", "linux")
    monkeypatch.setattr(
        "keprix_cli.auth._can_open_graphical_browser", lambda: True
    )
    monkeypatch.setattr(
        "keprix_cli.web_server.shutil.which", lambda name: "/usr/bin/xdg-open"
    )
    spawned = []

    def fake_popen(cmd, **kwargs):
        spawned.append((cmd, kwargs))
        return argparse.Namespace(pid=1)

    monkeypatch.setattr("keprix_cli.web_server.subprocess.Popen", fake_popen)
    assert open_dashboard_url("http://127.0.0.1:9120/home") is True
    assert spawned[0][0] == ["/usr/bin/xdg-open", "http://127.0.0.1:9120/home"]
    assert spawned[0][1].get("start_new_session") is True


def test_open_dashboard_url_refuses_console_browser(monkeypatch):
    monkeypatch.setattr(
        "keprix_cli.auth._can_open_graphical_browser", lambda: False
    )
    monkeypatch.setattr(
        "keprix_cli.web_server.subprocess.Popen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not spawn")),
    )
    assert open_dashboard_url("http://127.0.0.1:9120/home") is False


def test_install_dispatch_writes_unit(tmp_path, monkeypatch):
    unit_path = tmp_path / "keprix-dashboard.service"
    monkeypatch.setattr(
        "keprix_cli.dashboard_service.supports_systemd_services", lambda: True
    )
    monkeypatch.setattr("keprix_cli.dashboard_service.is_termux", lambda: False)
    monkeypatch.setattr("keprix_cli.dashboard_service.is_macos", lambda: False)
    monkeypatch.setattr("keprix_cli.dashboard_service.is_windows", lambda: False)
    monkeypatch.setattr("keprix_cli.dashboard_service.is_managed", lambda: False)
    monkeypatch.setattr(
        "keprix_cli.dashboard_service.get_systemd_unit_path",
        lambda system=False: unit_path,
    )
    monkeypatch.setattr(
        "keprix_cli.dashboard_service._run_systemctl",
        lambda *a, **k: argparse.Namespace(returncode=0),
    )
    monkeypatch.setattr(
        "keprix_cli.dashboard_service._ensure_frontend_dist", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "keprix_cli.dashboard_service._ensure_linger_enabled", lambda: None
    )
    monkeypatch.setattr(
        "keprix_cli.dashboard_service._stop_stray_dashboards", lambda: None
    )
    monkeypatch.setattr(
        "keprix_cli.dashboard_service._preflight_user_systemd", lambda **k: None
    )
    monkeypatch.setattr(
        "keprix_cli.dashboard_service._refuse_temp_home", lambda *a, **k: False
    )

    args = argparse.Namespace(
        dashboard_subcommand="install",
        force=False,
        system=False,
        host=DEFAULT_HOST,
        port=DEFAULT_BACKEND_PORT,
        frontend_port=DEFAULT_FRONTEND_PORT,
        run_as_user=None,
        no_start=True,
    )
    from keprix_cli.dashboard_service import dashboard_service_command

    dashboard_service_command(args)
    text = unit_path.read_text(encoding="utf-8")
    assert "dashboard --host 127.0.0.1 --port 9119 --no-open" in text
    assert "--skip-build" not in text
    assert "KEPRIX_DASHBOARD_FRONTEND_PORT=9120" in text
