import { describe, expect, it } from "vitest";
import {
  contrastRatio,
  contrastText,
  ensureInteractiveAccent,
  ensureMutedText,
} from "@/theme/contrast";

describe("theme contrast helpers", () => {
  it("darkens pastel light-mode accents until buttons pass WCAG AA", () => {
    const accent = ensureInteractiveAccent("#8a79ab", "#ffffff", "light");
    expect(contrastRatio(accent, "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(contrastText(accent), accent)).toBeGreaterThanOrEqual(4.5);
  });

  it("fixes near-white dark-mode primaries", () => {
    const accent = ensureInteractiveAccent("#fafafa", "#1a1d23", "dark");
    expect(contrastRatio(accent, "#1a1d23")).toBeGreaterThanOrEqual(4.5);
  });

  it("keeps muted text readable on paper", () => {
    const muted = ensureMutedText("#c4b5fd", "#ffffff", "light");
    expect(contrastRatio(muted, "#ffffff")).toBeGreaterThanOrEqual(4.5);
  });
});
