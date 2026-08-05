import { describe, expect, it } from "vitest";
import { resolveSettingsNavValue, settingsNavigation, visibleSettingsNavigation } from "@/lib/settings-navigation";

describe("settings navigation", () => {
  it("selects parent tabs for nested settings routes", () => {
    expect(resolveSettingsNavValue("/settings/account/profile", settingsNavigation)).toBe("/settings/account");
    expect(resolveSettingsNavValue("/settings/voice/wake-words", settingsNavigation)).toBe("/settings/voice");
    expect(resolveSettingsNavValue("/settings", settingsNavigation)).toBe("/settings");
  });

  it("hides admin-only settings links for non-admin users", () => {
    expect(visibleSettingsNavigation(false).map((item) => item.href)).not.toContain("/settings/users");
    expect(visibleSettingsNavigation(true).map((item) => item.href)).toContain("/settings/users");
  });
});
