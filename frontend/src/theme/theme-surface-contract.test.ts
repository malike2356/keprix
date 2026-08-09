import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const SOURCE_ROOTS = ["src/app", "src/components"];
const SOURCE_EXTENSIONS = new Set([".css", ".ts", ".tsx"]);
const ALLOW_MARKER = "theme-surface-ok:";

// Neutral literals used as page or component surfaces force one colour scheme onto
// the other. Brand accents, status colours, charts, image overlays, and canvas
// rendering are deliberately outside this rule.
const FORCED_NEUTRAL_SURFACE =
  /(?:background(?:Color)?|bgcolor|border(?:Color)?)\s*:\s*["'`](?:#fff(?:fff)?|#f7f7f5|#111827|#06060e|rgba\(\s*(?:8\s*,\s*8\s*,\s*20|10\s*,\s*10\s*,\s*22)[^)]*\))/i;

function sourceFiles(root: string): string[] {
  return fs.readdirSync(root, { withFileTypes: true }).flatMap((entry) => {
    const absolute = path.join(root, entry.name);
    if (entry.isDirectory()) {
      return sourceFiles(absolute);
    }
    return SOURCE_EXTENSIONS.has(path.extname(entry.name)) ? [absolute] : [];
  });
}

describe("theme surface contract", () => {
  it("does not hardcode light or dark neutral component surfaces", () => {
    const violations = SOURCE_ROOTS.flatMap((sourceRoot) =>
      sourceFiles(path.resolve(process.cwd(), sourceRoot)).flatMap((file) =>
        fs
          .readFileSync(file, "utf8")
          .split("\n")
          .map((line, index) => ({ file, line, lineNumber: index + 1 }))
          .filter(({ line }) => FORCED_NEUTRAL_SURFACE.test(line) && !line.includes(ALLOW_MARKER))
          .map(({ file: matchedFile, lineNumber, line }) =>
            `${path.relative(process.cwd(), matchedFile)}:${lineNumber} ${line.trim()}`,
          ),
      ),
    );

    expect(
      violations,
      `Use MUI palette tokens, marketing colours, or --kp-* CSS variables. ` +
        `Only fixed technical surfaces may use ${ALLOW_MARKER} with a reason.`,
    ).toEqual([]);
  });
});
