import { ThemeProvider } from "@mui/material/styles";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import BuiltAppRouteLayout from "@/app/(workspace)/apps/[slug]/layout";
import type { BuiltAppManifest } from "@/components/built-app/types";
import { keprixTheme } from "@/theme/keprix-theme";

let mockSlug = "starter";
let mockPathname = "/apps/starter/reports";
let mockState: {
  manifest?: BuiltAppManifest;
  error?: unknown;
  isLoading?: boolean;
} = {};

vi.mock("next/navigation", () => ({
  useParams: () => ({ slug: mockSlug }),
  usePathname: () => mockPathname,
}));

vi.mock("@/hooks/useBuiltAppManifest", () => ({
  useBuiltAppManifest: () => mockState,
}));

const starterManifest: BuiltAppManifest = {
  id: "starter",
  label: "Starter app",
  entry: "/apps/starter",
  navigation: {
    style: "sections",
    items: [
      { id: "dashboard", label: "Dashboard", href: "/apps/starter" },
      { id: "reports", label: "Reports", href: "/apps/starter/reports" },
      { id: "settings", label: "Settings", href: "/apps/starter/settings" },
    ],
  },
};

function renderLayout() {
  return render(
    <ThemeProvider theme={keprixTheme}>
      <BuiltAppRouteLayout>
        <div>Starter content</div>
      </BuiltAppRouteLayout>
    </ThemeProvider>,
  );
}

afterEach(() => {
  cleanup();
  mockSlug = "starter";
  mockPathname = "/apps/starter/reports";
  mockState = {};
});

describe("BuiltAppRouteLayout", () => {
  it("renders BuiltAppLayout with section labels", () => {
    mockState = { manifest: starterManifest, isLoading: false };
    renderLayout();

    expect(screen.getByRole("heading", { name: "Starter app" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Reports" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Starter content")).toBeInTheDocument();
  });

  it("unknown slug shows error state", () => {
    mockSlug = "missing";
    mockState = { error: new Error("Failed to load built app manifest"), isLoading: false };
    renderLayout();

    expect(screen.getByText("Failed to load built app manifest")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to workspace" })).toHaveAttribute("href", "/home");
  });
});
