import { describe, expect, it } from "vitest";
import { keprixTypography } from "./typography";

describe("keprixTypography", () => {
  it("uses Google AI Studio typefaces", () => {
    expect(keprixTypography.fontFamily).toContain("Google Sans Flex");
    expect(keprixTypography.fontFamily).toContain("Google Sans Text");
    expect(keprixTypography.fontFamilyDisplay).toContain("Google Sans Flex");
    expect(keprixTypography.fontFamilyMono).toContain("Google Sans Code");
  });
});
