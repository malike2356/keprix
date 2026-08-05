"""Tests for extensions/compatibility.py."""

from __future__ import annotations

import pytest

import keprix.extensions.compatibility as compat_module
from keprix.extensions.compatibility import (
    check_features_available,
    check_version_compatible,
    features_available,
    _Version,
)


def test_version_parse():
    v = _Version.parse("1.2.3")
    assert v.major == 1 and v.minor == 2 and v.patch == 3


def test_version_comparison():
    assert _Version.parse("0.3.0") < _Version.parse("0.4.0")
    assert _Version.parse("1.0.0") > _Version.parse("0.99.99")
    assert _Version.parse("0.3.1") == _Version.parse("0.3.1")


def test_version_parse_invalid():
    with pytest.raises(ValueError):
        _Version.parse("not_a_version")


def test_version_compatible_same_version(monkeypatch):
    monkeypatch.setattr(compat_module, "KEPRIX_VERSION", "0.3.0")
    ok, reason = check_version_compatible("0.3.0")
    assert ok
    assert reason == ""


def test_version_compatible_newer_running(monkeypatch):
    monkeypatch.setattr(compat_module, "KEPRIX_VERSION", "0.4.5")
    ok, _ = check_version_compatible("0.3.0")
    assert ok


def test_version_incompatible_too_old(monkeypatch):
    monkeypatch.setattr(compat_module, "KEPRIX_VERSION", "0.2.9")
    ok, reason = check_version_compatible("0.3.0")
    assert not ok
    assert "0.3.0" in reason


def test_features_available_returns_set():
    fa = features_available()
    assert "billing" in fa
    assert "providers" in fa
    assert "notion" in fa


def test_check_features_available_all_present():
    missing = check_features_available(["billing", "providers"])
    assert missing == []


def test_check_features_available_missing():
    missing = check_features_available(["billing", "nonexistent_feature"])
    assert "nonexistent_feature" in missing
    assert "billing" not in missing
