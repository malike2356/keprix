import { describe, expect, it } from "vitest";
import { paletteAlignedWithMode } from "@/components/providers/ThemeRegistry";
import { getKeprixColors } from "@/theme/tokens/colors";

describe("paletteAlignedWithMode", () => {
  it("accepts light tokens in light mode", () => {
    expect(paletteAlignedWithMode(getKeprixColors("light"), "light")).toBe(true);
  });

  it("accepts dark tokens in dark mode", () => {
    expect(paletteAlignedWithMode(getKeprixColors("dark"), "dark")).toBe(true);
  });

  it("rejects dark paper while mode is light", () => {
    expect(paletteAlignedWithMode(getKeprixColors("dark"), "light")).toBe(false);
  });

  it("rejects light paper while mode is dark", () => {
    expect(paletteAlignedWithMode(getKeprixColors("light"), "dark")).toBe(false);
  });
});
