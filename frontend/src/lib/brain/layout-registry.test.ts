import { describe, expect, it } from "vitest";
import { readClustersPreference, readLayoutPreference, writeClustersPreference, writeLayoutPreference } from "@/lib/brain/layout-registry";

describe("layout preferences", () => {
  it("persists layout and cluster preferences per workspace", () => {
    writeLayoutPreference("workspace-a", "radial");
    writeClustersPreference("workspace-a", false);
    expect(readLayoutPreference("workspace-a")).toBe("radial");
    expect(readClustersPreference("workspace-a")).toBe(false);

    writeLayoutPreference("workspace-b", "temporal");
    writeClustersPreference("workspace-b", true);
    expect(readLayoutPreference("workspace-b")).toBe("temporal");
    expect(readClustersPreference("workspace-b")).toBe(true);
  });
});
