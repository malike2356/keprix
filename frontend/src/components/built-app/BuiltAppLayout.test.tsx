import { ThemeProvider } from "@mui/material/styles";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import BuiltAppLayout from "@/components/built-app/BuiltAppLayout";
import type { BuiltAppManifest } from "@/components/built-app/types";
import { activeNavItem, normalizeBuiltAppManifest } from "@/lib/built-app-manifest";
import { keprixTheme } from "@/theme/keprix-theme";

let mockPathname = "/apps/demo/finance";

vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}));

const demoManifest: BuiltAppManifest = {
  id: "demo",
  label: "Demo app",
  description: "Demo app sections.",
  entry: "/apps/demo",
  version: "1.0.0",
  navigation: {
    style: "sections",
    items: [
      { id: "overview", label: "Overview", href: "/apps/demo" },
      { id: "finance", label: "Finance", href: "/apps/demo/finance" },
      { id: "settings", label: "Settings", href: "/apps/demo/settings" },
    ],
  },
};

function renderLayout(manifest: BuiltAppManifest = demoManifest) {
  return render(
    <ThemeProvider theme={keprixTheme}>
      <BuiltAppLayout manifest={manifest}>
        <div>App content</div>
      </BuiltAppLayout>
    </ThemeProvider>,
  );
}

afterEach(() => {
  cleanup();
  mockPathname = "/apps/demo/finance";
});

describe("BuiltAppLayout", () => {
  it("renders section nav from manifest", () => {
    renderLayout();

    const nav = screen.getByRole("tablist", { name: "App sections" });
    expect(within(nav).getByRole("tab", { name: "Overview" })).toBeInTheDocument();
    expect(within(nav).getByRole("tab", { name: "Finance" })).toBeInTheDocument();
    expect(screen.getByText("Back to workspace")).toBeInTheDocument();
    expect(screen.getByText("All apps")).toBeInTheDocument();
  });

  it("highlights active section for pathname /apps/demo/finance", () => {
    renderLayout();

    expect(screen.getByRole("tab", { name: "Finance" })).toHaveAttribute("aria-selected", "true");
    expect(activeNavItem(demoManifest, "/apps/demo/finance/deep")?.id).toBe("finance");
  });

  it("sub-rail layout renders two columns when style is sub_rail", () => {
    renderLayout({
      ...demoManifest,
      navigation: {
        ...demoManifest.navigation,
        style: "sub_rail",
        items: demoManifest.navigation?.items ?? [],
      },
    });

    expect(screen.getByRole("navigation", { name: "App sub navigation" })).toBeInTheDocument();
    expect(screen.getByText("App content")).toBeInTheDocument();
  });

  it("normalizes valid manifests and rejects hrefs outside the app prefix", () => {
    expect(normalizeBuiltAppManifest(demoManifest).id).toBe("demo");
    expect(() =>
      normalizeBuiltAppManifest({
        ...demoManifest,
        navigation: { items: [{ id: "bad", label: "Bad", href: "/admin" }] },
      }),
    ).toThrow("navigation href");
  });
});
