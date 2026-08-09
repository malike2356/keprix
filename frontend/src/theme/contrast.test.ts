import { describe, expect, it } from "vitest";
import {
  contrastRatio,
  contrastText,
  ensureInteractiveAccent,
  ensureMutedText,
  ensurePrimaryText,
  severityScale,
  softStatusColors,
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

  it("rejects dark foreground on dark paper", () => {
    const text = ensurePrimaryText("#111827", "#0a0a0a", "dark");
    expect(contrastRatio(text, "#0a0a0a")).toBeGreaterThanOrEqual(4.5);
  });

  it("builds soft status fills with readable text", () => {
    const soft = softStatusColors("#F59E0B", "#0a0a0a", "dark");
    expect(contrastRatio(soft.color, soft.backgroundColor)).toBeGreaterThanOrEqual(4.5);
  });

  it("uses dark-tinted severity.light in dark mode", () => {
    const scale = severityScale("#F59E0B", "dark");
    expect(contrastRatio(scale.softContrastText, scale.light)).toBeGreaterThanOrEqual(4.5);
  });
});
