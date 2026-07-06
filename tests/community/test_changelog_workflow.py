"""Changelog workflow fixtures and release automation compatibility."""

from __future__ import annotations

from pathlib import Path

from tests.community.changelog_parse import parse_changelog

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "changelog-samples"


def test_released_and_unreleased_fixture_still_parses() -> None:
    markdown = (FIXTURES / "released-and-unreleased.md").read_text(encoding="utf-8")
    releases = parse_changelog(markdown)
    assert len(releases) == 2
    assert releases[0].is_unreleased
    assert releases[1].version == "0.1.0"


def test_root_changelog_has_unreleased_and_shipped_sections() -> None:
    markdown = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    releases = parse_changelog(markdown)
    unreleased = [r for r in releases if r.is_unreleased]
    shipped = [r for r in releases if not r.is_unreleased]
    assert unreleased, "CHANGELOG.md must keep ## [Unreleased] for release-please"
    assert shipped, "CHANGELOG.md must contain at least one released version"
    assert all(r.sections for r in releases)
