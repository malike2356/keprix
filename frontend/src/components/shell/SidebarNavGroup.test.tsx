import List from "@mui/material/List";
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import SidebarNavGroup from "@/components/shell/SidebarNavGroup";
import { defaultExpanded } from "@/hooks/useSidebarGroupState";
import { keprixTheme } from "@/theme/keprix-theme";

function renderGroup(expanded: boolean, onToggle = vi.fn()) {
  return render(
    <ThemeProvider theme={keprixTheme}>
      <SidebarNavGroup groupId="workspace" label="Workspace" expanded={expanded} onToggle={onToggle}>
        <List>Chat link</List>
      </SidebarNavGroup>
    </ThemeProvider>,
  );
}

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.clearAllMocks();
});

describe("SidebarNavGroup", () => {
  it("click header toggles aria-expanded", () => {
    const onToggle = vi.fn();
    const { rerender } = renderGroup(false, onToggle);
    const header = screen.getByRole("button", { name: "Workspace navigation group" });

    expect(header).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(header);
    expect(onToggle).toHaveBeenCalledTimes(1);

    rerender(
      <ThemeProvider theme={keprixTheme}>
        <SidebarNavGroup groupId="workspace" label="Workspace" expanded onToggle={onToggle}>
          <List>Chat link</List>
        </SidebarNavGroup>
      </ThemeProvider>,
    );
    expect(screen.getByRole("button", { name: "Workspace navigation group" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("default expands workspace group", () => {
    expect(defaultExpanded("workspace", "/home")).toBe(true);
    expect(defaultExpanded("research", "/home")).toBe(false);
  });

  it("uses seeded localStorage values across rerenders", () => {
    window.localStorage.setItem("keprix_nav_group_workspace", "0");
    const { rerender } = renderGroup(window.localStorage.getItem("keprix_nav_group_workspace") === "1");
    expect(screen.getByRole("button", { name: "Workspace navigation group" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );

    window.localStorage.setItem("keprix_nav_group_workspace", "1");
    rerender(
      <ThemeProvider theme={keprixTheme}>
        <SidebarNavGroup
          groupId="workspace"
          label="Workspace"
          expanded={window.localStorage.getItem("keprix_nav_group_workspace") === "1"}
          onToggle={vi.fn()}
        >
          <List>Chat link</List>
        </SidebarNavGroup>
      </ThemeProvider>,
    );
    expect(screen.getByRole("button", { name: "Workspace navigation group" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });
});
