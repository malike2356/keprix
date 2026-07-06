"""Keep a Changelog parser mirroring frontend/src/lib/changelog.ts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

RELEASE_HEADING = re.compile(r"^## \[(.+?)\](?: - (.+))?$")
SECTION_HEADING = re.compile(r"^### (.+)$")
LIST_ITEM = re.compile(r"^- (.+)$")


@dataclass
class ChangelogSection:
    category: str
    items: list[str] = field(default_factory=list)


@dataclass
class ChangelogRelease:
    version: str
    date: str | None
    is_unreleased: bool
    sections: list[ChangelogSection] = field(default_factory=list)


def parse_changelog(markdown: str) -> list[ChangelogRelease]:
    releases: list[ChangelogRelease] = []
    current: ChangelogRelease | None = None
    current_section: ChangelogSection | None = None

    for raw_line in markdown.split("\n"):
        line = raw_line.rstrip()

        release_match = RELEASE_HEADING.match(line)
        if release_match:
            version = release_match.group(1)
            current = ChangelogRelease(
                version=version,
                date=release_match.group(2),
                is_unreleased=version.lower() == "unreleased",
            )
            releases.append(current)
            current_section = None
            continue

        section_match = SECTION_HEADING.match(line)
        if section_match and current is not None:
            current_section = ChangelogSection(category=section_match.group(1))
            current.sections.append(current_section)
            continue

        item_match = LIST_ITEM.match(line)
        if item_match and current_section is not None:
            current_section.items.append(item_match.group(1))

    return releases
