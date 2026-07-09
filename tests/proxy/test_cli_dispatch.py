"""Tests for keprix proxy CLI dispatch."""

from __future__ import annotations

from unittest.mock import MagicMock

from keprix.proxy.cli_handlers import dispatch_credential_proxy


def test_credential_proxy_status_not_running(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    args = MagicMock()
    args.proxy_command = "status"
    rc = dispatch_credential_proxy(args)
    assert rc == 1
    assert "not running" in capsys.readouterr().out


def test_oauth_proxy_status_via_oauth_subcommand(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    args = MagicMock()
    args.proxy_command = "oauth"
    args.oauth_command = "status"
    rc = dispatch_credential_proxy(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "nous" in out
