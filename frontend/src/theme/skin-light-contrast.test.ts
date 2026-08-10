import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { contrastRatio, parseHex } from "@/theme/contrast";

const SKINS_CSS = path.resolve(process.cwd(), "public/themes/skins.css");

function lightSkinBlocks(css: string): Array<{ skin: string; body: string }> {
  const blocks: Array<{ skin: string; body: string }> = [];
  const re = /html(?!\.dark)\[data-skin="([^"]+)"\]\s*\{([^}]*)\}/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(css))) {
    blocks.push({ skin: match[1], body: match[2] });
  }
  return blocks;
}

function readVar(body: string, name: string): string | null {
  const match = body.match(new RegExp(`${name}\\s*:\\s*([^;]+);`));
  return match ? match[1].trim() : null;
}

describe("light skin text contrast", () => {
  it("keeps muted and body text readable on paper for every light skin", () => {
    const css = fs.readFileSync(SKINS_CSS, "utf8");
    const failures: string[] = [];
    for (const { skin, body } of lightSkinBlocks(css)) {
      const paper = readVar(body, "--card") || readVar(body, "--background") || "#ffffff";
      const muted = readVar(body, "--muted-foreground");
      const foreground = readVar(body, "--foreground");
      if (!parseHex(paper || "")) continue;
      if (muted && parseHex(muted) && contrastRatio(muted, paper!) < 5.5) {
        failures.push(`${skin} muted ${muted} on ${paper} = ${contrastRatio(muted, paper!).toFixed(2)}`);
      }
      if (foreground && parseHex(foreground) && contrastRatio(foreground, paper!) < 7) {
        failures.push(`${skin} foreground ${foreground} on ${paper} = ${contrastRatio(foreground, paper!).toFixed(2)}`);
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });
});
