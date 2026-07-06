"""Tests for WARDEN privacy module."""

from __future__ import annotations

import pytest

from keprix.personas.warden.auditor import Severity
from keprix.personas.warden.privacy import WardenPrivacy


@pytest.fixture
def privacy() -> WardenPrivacy:
    return WardenPrivacy()


def test_scan_detects_email(privacy: WardenPrivacy) -> None:
    result = privacy.scan("Contact us at user@example.com for support")
    assert any(f.pattern == "email" for f in result.findings)


def test_scan_detects_phone(privacy: WardenPrivacy) -> None:
    result = privacy.scan("Call +44 20 7946 0958 for assistance")
    assert any(f.pattern == "phone" for f in result.findings)


def test_scan_detects_api_key(privacy: WardenPrivacy) -> None:
    result = privacy.scan('key = "sk-abcdefghijklmnopqrstuvwxyz123456"')
    assert not result.passed
    assert any(f.severity == Severity.CRITICAL for f in result.findings)


def test_scan_sanitizes_secrets(privacy: WardenPrivacy) -> None:
    result = privacy.scan('token = "sk-abcdefghijklmnopqrstuvwxyz123456"')
    assert "sk-" not in result.sanitized_text


def test_scan_files_aggregates_findings(privacy: WardenPrivacy) -> None:
    result = privacy.scan_files(
        {
            "a.txt": "email: user@example.com",
            "b.txt": 'key = "sk-abcdefghijklmnopqrstuvwxyz123456"',
        }
    )
    assert len(result.findings) >= 2


def test_recommend_actions_for_secrets(privacy: WardenPrivacy) -> None:
    result = privacy.scan('key = "sk-abcdefghijklmnopqrstuvwxyz123456"')
    actions = privacy.recommend_actions(result)
    assert any("vault" in action.lower() for action in actions)
