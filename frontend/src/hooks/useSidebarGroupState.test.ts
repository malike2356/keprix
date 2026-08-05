import { describe, expect, it } from "vitest";
import {
  defaultExpanded,
  nextOpenGroupId,
  resolveOpenGroupId,
} from "@/hooks/useSidebarGroupState";
import type { NavItem } from "@/lib/navigation";

const groups = [
  { id: "workspace" as const, label: "Workspace" },
  { id: "admin" as const, label: "Admin" },
];

const items: NavItem[] = [
  { id: "home", label: "Home", href: "/home", icon: "home", group: "workspace" },
  { id: "control-center", label: "Admin", href: "/control-center", icon: "admin", group: "admin" },
];

describe("defaultExpanded", () => {
  it("keeps the workspace group open by default", () => {
    expect(defaultExpanded("workspace", "/home")).toBe(true);
  });

  it("collapses other groups by default", () => {
    expect(defaultExpanded("admin", "/home")).toBe(false);
  });

  it("opens installed apps when on an app route", () => {
    expect(defaultExpanded("installed_apps", "/apps/foo")).toBe(true);
  });
});

describe("nextOpenGroupId", () => {
  it("opens a closed group", () => {
    expect(nextOpenGroupId(null, "admin")).toBe("admin");
  });

  it("collapses the currently open group when toggled again", () => {
    expect(nextOpenGroupId("admin", "admin")).toBeNull();
  });

  it("switches to a different group", () => {
    expect(nextOpenGroupId("workspace", "admin")).toBe("admin");
  });
});

describe("resolveOpenGroupId", () => {
  it("opens the group containing the active route", () => {
    expect(resolveOpenGroupId(groups, items, "/control-center")).toBe("admin");
  });

  it("falls back to the workspace group when no route matches", () => {
    expect(resolveOpenGroupId(groups, items, "/unknown")).toBe("workspace");
  });

  it("returns null when there are no groups", () => {
    expect(resolveOpenGroupId([], items, "/home")).toBeNull();
  });
});
