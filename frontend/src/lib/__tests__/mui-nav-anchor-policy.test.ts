import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const LINK_COMPONENT = /component=\{Link\}/;
const NEXT_LINK_COMPONENT = /component=\{NextLink\}/;

const SRC_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

function walkSourceFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name === ".next") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walkSourceFiles(full));
      continue;
    }
    if (!/\.(tsx|ts|jsx|js)$/.test(entry.name)) continue;
    out.push(full);
  }
  return out;
}

describe("mui nav anchor policy", () => {
  it('forbids passing next/link as MUI component; use component="a" href=...', () => {
    const offenders: string[] = [];
    for (const file of walkSourceFiles(SRC_ROOT)) {
      const text = fs.readFileSync(file, "utf8");
      if (LINK_COMPONENT.test(text) || NEXT_LINK_COMPONENT.test(text)) {
        offenders.push(path.relative(SRC_ROOT, file));
      }
    }

    expect(
      offenders,
      'Found MUI + next/link soft-nav usage. Prefer component="a" href=... (see components/ui/muiNavAnchor.ts). Offenders: ' +
        offenders.join(", "),
    ).toEqual([]);
  });
});
