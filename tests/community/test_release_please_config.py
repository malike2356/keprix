"""release-please configuration and manifest alignment."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "release-please-config.json"
MANIFEST = ROOT / ".release-please-manifest.json"
CHANGELOG = ROOT / "CHANGELOG.md"
WORKFLOW = ROOT / ".github" / "workflows" / "release-please.yml"

RELEASE_HEADING = re.compile(r"^## \[(.+?)\](?: - .+)?$", re.MULTILINE)


def latest_released_version(changelog_text: str) -> str | None:
    for match in RELEASE_HEADING.finditer(changelog_text):
        version = match.group(1)
        if version.lower() != "unreleased":
            return version
    return None


def test_release_please_config_exists_and_parses() -> None:
    assert CONFIG.is_file()
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert data["packages"]["."].get("changelog-path") == "CHANGELOG.md"
    assert data["packages"]["."].get("release-type") == "python"


def test_release_please_manifest_parses() -> None:
    assert MANIFEST.is_file()
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(data["."], str)
    assert re.fullmatch(r"\d+\.\d+\.\d+", data["."])


def test_manifest_version_matches_latest_changelog_release() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["."]
    changelog = CHANGELOG.read_text(encoding="utf-8")
    latest = latest_released_version(changelog)
    assert latest is not None, "CHANGELOG.md should contain at least one released version"
    assert manifest == latest


def test_release_please_workflow_exists() -> None:
    assert WORKFLOW.is_file()
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "googleapis/release-please-action@v4" in text
    assert "release-please-config.json" in text
