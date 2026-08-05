"""Tests for upgrade/changelog.py and upgrade/versions.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.upgrade.changelog import entries_between, load_changelog, parse_changelog
from keprix.upgrade.versions import latest_version, sort_versions, versions_between

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CHANGELOG_PATH = FIXTURES / "CHANGELOG.yaml"


def test_sort_versions():
    assert sort_versions(["0.7.0", "0.3.0", "0.10.0", "0.2.0"]) == [
        "0.2.0", "0.3.0", "0.7.0", "0.10.0",
    ]


def test_versions_between():
    available = ["0.1.0", "0.2.0", "0.3.0", "0.5.0", "0.7.0"]
    assert versions_between("0.3.0", "0.7.0", available) == ["0.5.0", "0.7.0"]


def test_latest_version():
    assert latest_version(["0.3.0", "0.7.0", "0.5.0"]) == "0.7.0"
    assert latest_version([]) is None


def test_load_changelog_fixture():
    releases = load_changelog(CHANGELOG_PATH)
    versions = [r.version for r in releases]
    assert versions == ["0.4.0", "0.5.0", "0.6.0", "0.7.0"]


def test_entries_between_collects_releases_in_range():
    releases = load_changelog(CHANGELOG_PATH)
    entries = entries_between("0.3.0", "0.7.0", releases)
    types = [e["type"] for e in entries]
    assert types.count("feature") == 5
    assert types.count("config_migration") == 2
    assert types.count("deprecation") == 1
    assert types.count("breaking") == 1
    assert all("version" in e for e in entries)


def test_entries_between_excludes_from_version():
    releases = load_changelog(CHANGELOG_PATH)
    entries = entries_between("0.5.0", "0.7.0", releases)
    versions = {e["version"] for e in entries}
    assert "0.4.0" not in versions
    assert "0.5.0" not in versions
    assert "0.6.0" in versions
    assert "0.7.0" in versions


def test_parse_changelog_invalid_data():
    assert parse_changelog(None) == []
    assert parse_changelog({"not": "a list"}) == []


def test_load_changelog_missing_file(tmp_path: Path):
    assert load_changelog(tmp_path / "missing.yaml") == []
