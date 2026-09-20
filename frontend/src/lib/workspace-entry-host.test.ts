import { describe, expect, it } from "vitest";
import { isWorkspaceEntryHost } from "@/lib/workspace-entry-host";

describe("isWorkspaceEntryHost", () => {
  it("treats local dashboard and app.keprixai.com as the workspace", () => {
    expect(isWorkspaceEntryHost("127.0.0.1:60085")).toBe(true);
    expect(isWorkspaceEntryHost("localhost:9119")).toBe(true);
    expect(isWorkspaceEntryHost("app.keprixai.com")).toBe(true);
  });

  it("leaves the public marketing hostname on /", () => {
    expect(isWorkspaceEntryHost("keprixai.com")).toBe(false);
    expect(isWorkspaceEntryHost("www.keprixai.com")).toBe(false);
  });
});
