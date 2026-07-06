import { ThemeProvider } from "@mui/material/styles";
import { cleanup, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import AsyncView from "@/components/ui/loading/AsyncView";
import SkeletonTable from "@/components/ui/loading/SkeletonTable";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";
import { keprixTheme } from "@/theme/keprix-theme";

function renderWithTheme(ui: ReactElement) {
  return render(<ThemeProvider theme={keprixTheme}>{ui}</ThemeProvider>);
}

afterEach(() => {
  cleanup();
});

describe("SkeletonTable", () => {
  it("renders the expected number of body rows", () => {
    const { container } = renderWithTheme(<SkeletonTable rows={5} columns={3} />);
    const rows = container.querySelectorAll("tbody tr");
    expect(rows).toHaveLength(5);
  });
});

describe("AsyncView", () => {
  it("shows skeleton while loading", () => {
    renderWithTheme(
      <AsyncView loading skeleton={<div data-testid="loading-skeleton" />}>
        <div data-testid="loaded-content">Ready</div>
      </AsyncView>,
    );
    expect(screen.getByTestId("loading-skeleton")).toBeInTheDocument();
    expect(screen.queryByTestId("loaded-content")).not.toBeInTheDocument();
  });

  it("shows children when not loading", () => {
    renderWithTheme(
      <AsyncView loading={false} skeleton={<div data-testid="loading-skeleton" />}>
        <div data-testid="loaded-content">Ready</div>
      </AsyncView>,
    );
    expect(screen.getByTestId("loaded-content")).toBeInTheDocument();
    expect(screen.queryByTestId("loading-skeleton")).not.toBeInTheDocument();
  });
});

describe("usePrefersReducedMotion", () => {
  it("returns true when the user prefers reduced motion", () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: query === "(prefers-reduced-motion: reduce)",
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    function Probe() {
      const reduced = usePrefersReducedMotion();
      return <span data-testid="reduced">{String(reduced)}</span>;
    }

    renderWithTheme(<Probe />);
    expect(screen.getByTestId("reduced")).toHaveTextContent("true");
    vi.unstubAllGlobals();
  });
});
