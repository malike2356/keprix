import { describe, expect, it } from "vitest";
import { mobilePrimaryNavigation, primaryNavigation } from "@/lib/navigation";

describe("navigation architecture", () => {
  it("keeps canonical top-level entry points in the primary workspace group", () => {
    const canonical = ["home", "chat", "brain", "skills", "tasks", "tools", "voice"];
    const items = primaryNavigation.filter((item) => canonical.includes(item.id));

    expect(items.map((item) => item.id)).toEqual(canonical);
    expect(items.every((item) => item.group === "workspace")).toBe(true);
    expect(items.map((item) => item.href)).toEqual([
      "/home",
      "/chat",
      "/brain/graph",
      "/skills",
      "/tasks",
      "/admin/tools",
      "/voice",
    ]);
  });

  it("uses a compact mobile tab set", () => {
    expect(mobilePrimaryNavigation.map((item) => item.id)).toEqual(["home", "chat", "brain", "tasks", "settings", "files"]);
  });
});
