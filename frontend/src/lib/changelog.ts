import { readFileSync } from "fs";
import path from "path";

export type ChangelogSection = {
  category: string;
  items: string[];
};

export type ChangelogRelease = {
  version: string;
  date: string | null;
  isUnreleased: boolean;
  sections: ChangelogSection[];
};

const RELEASE_HEADING = /^## \[(.+?)\](?: - (.+))?$/;
const SECTION_HEADING = /^### (.+)$/;
const LIST_ITEM = /^- (.+)$/;

export function parseChangelog(markdown: string): ChangelogRelease[] {
  const releases: ChangelogRelease[] = [];
  let current: ChangelogRelease | null = null;
  let currentSection: ChangelogSection | null = null;

  for (const rawLine of markdown.split("\n")) {
    const line = rawLine.trimEnd();

    const releaseMatch = line.match(RELEASE_HEADING);
    if (releaseMatch) {
      const version = releaseMatch[1];
      current = {
        version,
        date: releaseMatch[2] ?? null,
        isUnreleased: version.toLowerCase() === "unreleased",
        sections: [],
      };
      releases.push(current);
      currentSection = null;
      continue;
    }

    const sectionMatch = line.match(SECTION_HEADING);
    if (sectionMatch && current) {
      currentSection = { category: sectionMatch[1], items: [] };
      current.sections.push(currentSection);
      continue;
    }

    const itemMatch = line.match(LIST_ITEM);
    if (itemMatch && currentSection) {
      currentSection.items.push(itemMatch[1]);
    }
  }

  return releases;
}

export function loadChangelog(): ChangelogRelease[] {
  const changelogPath = path.join(process.cwd(), "..", "CHANGELOG.md");
  const markdown = readFileSync(changelogPath, "utf8");
  return parseChangelog(markdown);
}
