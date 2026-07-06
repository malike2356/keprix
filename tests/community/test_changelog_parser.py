"""Changelog markdown parser compatibility (Keep a Changelog + git-cliff output)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.community.changelog_parse import parse_changelog

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "changelog-samples"


@pytest.mark.parametrize(
    "fixture_name",
    ["unreleased-only.md", "released-and-unreleased.md", "git-cliff-sample-output.md"],
)
def test_fixture_parses_without_error(fixture_name: str) -> None:
    markdown = (FIXTURES / fixture_name).read_text(encoding="utf-8")
    releases = parse_changelog(markdown)
    assert releases, f"{fixture_name} should contain at least one release"
    assert all(release.sections for release in releases), f"{fixture_name} missing sections"


def test_unreleased_fixture_flags_unreleased() -> None:
    markdown = (FIXTURES / "unreleased-only.md").read_text(encoding="utf-8")
    releases = parse_changelog(markdown)
    assert releases[0].is_unreleased is True
    assert releases[0].version == "Unreleased"


def test_released_fixture_has_version_and_date() -> None:
    markdown = (FIXTURES / "released-and-unreleased.md").read_text(encoding="utf-8")
    releases = parse_changelog(markdown)
    shipped = [r for r in releases if not r.is_unreleased]
    assert len(shipped) == 1
    assert shipped[0].version == "0.1.0"
    assert shipped[0].date == "2026-07-05"


def test_git_cliff_scope_bullets_parsed_as_list_items() -> None:
    markdown = (FIXTURES / "git-cliff-sample-output.md").read_text(encoding="utf-8")
    releases = parse_changelog(markdown)
    added = next(s for s in releases[0].sections if s.category == "Added")
    assert any("**frontend:**" in item for item in added.items)


def test_root_changelog_md_parses() -> None:
    root = Path(__file__).resolve().parents[2]
    markdown = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    releases = parse_changelog(markdown)
    assert any(r.is_unreleased for r in releases)
    assert any(not r.is_unreleased for r in releases)
