"""Smoke tests for Prompt 18 CLI observability commands."""

from __future__ import annotations

import argparse

import pytest


def test_cmd_status_delegates(monkeypatch):
    calls: list[bool] = []
    monkeypatch.setattr("keprix_cli.status.show_status", lambda args: calls.append(True))

    from keprix_cli.main import cmd_status

    cmd_status(argparse.Namespace(all=False, deep=False))
    assert calls


def test_cmd_doctor_delegates(monkeypatch):
    calls: list[bool] = []
    monkeypatch.setattr("keprix_cli.doctor.run_doctor", lambda args: calls.append(True))

    from keprix_cli.main import cmd_doctor

    cmd_doctor(argparse.Namespace(fix=False, ack=None))
    assert calls


def test_show_status_prints_core_sections(monkeypatch, capsys):
    monkeypatch.setattr("keprix_cli.config.load_config", lambda: {"model": {"default": "test-model"}})
    monkeypatch.setattr("keprix_cli.status._effective_provider_label", lambda: "openrouter")
    monkeypatch.setattr("keprix_cli.status._configured_model_label", lambda _cfg: "test-model")
    monkeypatch.setattr(
        "keprix_cli.auth.get_anthropic_key",
        lambda: "",
    )
    monkeypatch.setattr(
        "keprix_cli.auth.get_nous_auth_status",
        lambda: {},
    )
    monkeypatch.setattr(
        "keprix_cli.auth.get_codex_auth_status",
        lambda: {},
    )
    monkeypatch.setattr(
        "keprix_cli.auth.get_qwen_auth_status",
        lambda: {},
    )
    monkeypatch.setattr(
        "keprix_cli.auth.get_minimax_oauth_auth_status",
        lambda: {},
    )
    monkeypatch.setattr(
        "gateway.platform_registry.platform_registry",
        type(
            "Registry",
            (),
            {"list_platforms": staticmethod(lambda: [])},
        )(),
    )
    monkeypatch.setattr(
        "keprix_cli.gateway.get_gateway_runtime_snapshot",
        lambda: type(
            "Snapshot",
            (),
            {"gateway_pids": [], "service_managed": False},
        )(),
    )

    from keprix_cli.status import show_status

    show_status(argparse.Namespace(all=False, deep=False))
    output = capsys.readouterr().out.lower()
    assert "environment" in output
    assert "gateway" in output or "cron" in output
