"""Load and filter Keprix CHANGELOG.yaml for upgrade analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .versions import version_gt, version_lte, version_tuple


@dataclass
class ChangelogRelease:
    """One release block from CHANGELOG.yaml."""
    version: str
    date: str = ""
    entries: list[dict[str, Any]] = field(default_factory=list)


def parse_changelog(data: Any) -> list[ChangelogRelease]:
    """Parse raw YAML data into release objects."""
    if not isinstance(data, list):
        return []
    releases: list[ChangelogRelease] = []
    for block in data:
        if not isinstance(block, dict):
            continue
        version = str(block.get("version", "")).strip()
        if not version:
            continue
        entries = block.get("entries") or []
        if not isinstance(entries, list):
            entries = []
        releases.append(
            ChangelogRelease(
                version=version,
                date=str(block.get("date", "")),
                entries=[e for e in entries if isinstance(e, dict)],
            )
        )
    return releases


def load_changelog(path: Path) -> list[ChangelogRelease]:
    """Load CHANGELOG.yaml from disk. Returns empty list if missing or invalid."""
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    return parse_changelog(data)


def entries_between(
    from_version: str,
    to_version: str,
    releases: list[ChangelogRelease],
) -> list[dict[str, Any]]:
    """Return flat changelog entries for versions in (from_version, to_version].

    Each returned entry includes a ``version`` key with the release it came from.
    """
    flat: list[dict[str, Any]] = []
    for release in sorted(releases, key=lambda r: version_tuple(r.version)):
        if not version_gt(release.version, from_version):
            continue
        if not version_lte(release.version, to_version):
            continue
        for entry in release.entries:
            tagged = dict(entry)
            tagged["version"] = release.version
            flat.append(tagged)
    return flat


def release_versions(releases: list[ChangelogRelease]) -> list[str]:
    """Return sorted version strings from changelog releases."""
    from .versions import sort_versions

    return sort_versions([r.version for r in releases])
