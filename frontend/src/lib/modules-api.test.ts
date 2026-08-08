import { describe, expect, it } from "vitest";
import {
  formatModuleCategory,
  formatModuleStatus,
  moduleStatusColor,
} from "@/lib/modules-api";

describe("modules-api helpers", () => {
  it("formats categories and statuses for the settings catalog", () => {
    expect(formatModuleCategory("cli_api")).toBe("Cli Api");
    expect(formatModuleCategory("automations")).toBe("Automations");
    expect(formatModuleStatus("available")).toBe("Available");
    expect(formatModuleStatus("partial")).toBe("Partial UI");
    expect(formatModuleStatus("cli_api")).toBe("CLI / API");
    expect(moduleStatusColor("available")).toBe("success");
    expect(moduleStatusColor("partial")).toBe("warning");
    expect(moduleStatusColor("cli_api")).toBe("default");
  });
});
