import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const roots = [
  join(process.cwd(), "src/app/(workspace)"),
  join(process.cwd(), "src/app/(admin)"),
  join(process.cwd(), "src/components"),
];

function sourceFiles(root: string): string[] {
  return readdirSync(root, { withFileTypes: true }).flatMap((entry) => {
    const path = join(root, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx)$/.test(entry.name) ? [path] : [];
  });
}

describe("destructive confirmation guard", () => {
  it("does not use the browser window.confirm API", () => {
    const offenders = roots
      .flatMap(sourceFiles)
      .filter((path) => !path.endsWith("no-window-confirm.test.ts"))
      .filter((path) => readFileSync(path, "utf8").includes(["window", "confirm"].join(".")));

    expect(offenders).toEqual([]);
  });
});
