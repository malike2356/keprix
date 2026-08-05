"""Tests for ops/credential_health.py."""

from __future__ import annotations

import os

import pytest

from keprix.providers.ops.credential_health import (
    CredentialHealth,
    CredentialStatus,
)


def test_missing_credential_is_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    health = CredentialHealth()
    result = health.check("anthropic")
    assert result.status == CredentialStatus.MISSING


def test_present_valid_credential_is_ok(monkeypatch):
    # Set a plausible-looking Anthropic key
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-" + "a" * 40)
    health = CredentialHealth()
    result = health.check("anthropic")
    assert result.status == CredentialStatus.OK


def test_invalid_format_credential_is_invalid(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-valid-key")
    health = CredentialHealth()
    result = health.check("anthropic")
    assert result.status == CredentialStatus.INVALID


def test_unknown_provider_is_unknown():
    health = CredentialHealth()
    result = health.check("does_not_exist")
    assert result.status == CredentialStatus.UNKNOWN


def test_provider_without_pattern_passes_nonempty(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "any-value-works")
    health = CredentialHealth()
    result = health.check("mistral")
    assert result.status == CredentialStatus.OK


def test_check_all_returns_all_providers():
    health = CredentialHealth()
    results = health.check_all()
    assert len(results) >= 5


def test_summary_counts():
    health = CredentialHealth()
    summary = health.summary()
    assert "total" in summary
    assert summary["total"] == summary["ok"] + summary["missing"] + summary["invalid"] + summary["unknown"]


def test_healthy_providers_only_returns_ok(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_" + "x" * 40)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    health = CredentialHealth()
    healthy = health.healthy_providers()
    assert "groq" in healthy
    assert "anthropic" not in healthy


def test_custom_map():
    health = CredentialHealth(custom_map={"myprovider": ("MY_SECRET_KEY", None)})
    result = health.check("myprovider")
    assert result.env_var == "MY_SECRET_KEY"
