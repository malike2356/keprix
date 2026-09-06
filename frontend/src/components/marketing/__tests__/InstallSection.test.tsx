import { ThemeProvider } from "@mui/material/styles";
import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { InstallSection } from "@/components/marketing/InstallSection";
import { Navbar } from "@/components/marketing/Navbar";
import { Hero } from "@/components/marketing/Hero";
import { keprixTheme } from "@/theme/keprix-theme";

beforeAll(() => {
  // Polyfill IntersectionObserver for ScrollReveal/framer-motion
  class MockIntersectionObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  }
  Object.defineProperty(window, "IntersectionObserver", {
    writable: true,
    configurable: true,
    value: MockIntersectionObserver,
  });

  // Polyfill matchMedia
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
});

vi.mock("@/components/providers/ThemeRegistry", () => ({
  useThemeMode: () => ({
    mode: "dark",
    skin: "default",
    skins: [],
    setMode: vi.fn(),
    setSkin: vi.fn(),
    toggleMode: vi.fn(),
  }),
}));

describe("Marketing Install & Deploy", () => {
  it("renders InstallSection with id='install' and curl command", () => {
    const { container } = render(
      <ThemeProvider theme={keprixTheme}>
        <InstallSection />
      </ThemeProvider>,
    );

    const section = container.querySelector("#install");
    expect(section).not.toBeNull();

    const deployAnchor = container.querySelector("#deploy");
    expect(deployAnchor).not.toBeNull();

    expect(
      screen.getByText(/curl -fsSL https:\/\/raw\.githubusercontent\.com\/malike2356\/keprix\/main\/scripts\/install\.sh \| bash/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Deploy Keprix on your own machine")).toBeInTheDocument();
  });

  it("renders Deploy free button in Navbar pointing to /#install", () => {
    render(
      <ThemeProvider theme={keprixTheme}>
        <Navbar />
      </ThemeProvider>,
    );

    const deployButtons = screen.getAllByRole("link", { name: /Deploy free/i });
    expect(deployButtons.length).toBeGreaterThan(0);
    expect(deployButtons[0]).toHaveAttribute("href", "/#install");
  });

  it("renders install command and anchor button in Hero", () => {
    render(
      <ThemeProvider theme={keprixTheme}>
        <Hero />
      </ThemeProvider>,
    );

    const installBtn = screen.getByRole("link", { name: /Install Community/i });
    expect(installBtn).toHaveAttribute("href", "#install");

    expect(
      screen.getAllByText(/curl -fsSL https:\/\/raw\.githubusercontent\.com\/malike2356\/keprix\/main\/scripts\/install\.sh \| bash/i).length,
    ).toBeGreaterThan(0);
  });
});
