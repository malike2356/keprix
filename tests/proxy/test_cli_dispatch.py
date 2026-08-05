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


def test_credential_proxy_rotate_writes_signal(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    args = MagicMock()
    args.proxy_command = "rotate"
    args.secret_ref = "anthropic-api-key"
    args.verify = True
    rc = dispatch_credential_proxy(args)
    assert rc == 0
    assert "with verification" in capsys.readouterr().out
    assert (tmp_path / "credential-rotation-signal.json").is_file()


def test_credential_proxy_fallback_status(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    args = MagicMock()
    args.proxy_command = "fallback"
    args.fallback_command = "status"
    rc = dispatch_credential_proxy(args)
    assert rc == 0
    assert '"enabled": false' in capsys.readouterr().out


def test_credential_proxy_vault_purge_requires_confirm(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    args = MagicMock()
    args.proxy_command = "vault-purge"
    args.confirm = False
    rc = dispatch_credential_proxy(args)
    assert rc == 1
    assert "requires --confirm" in capsys.readouterr().out
