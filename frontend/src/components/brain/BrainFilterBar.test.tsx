import { ThemeProvider } from "@mui/material/styles";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import BrainFilterBar from "@/components/brain/BrainFilterBar";
import { keprixTheme } from "@/theme/keprix-theme";
import type { BrainNodeKind } from "@/types/brain-graph";

vi.mock("@/lib/ce-api", () => ({
  ceApi: vi.fn(async () => ({ ok: true, json: async () => ({ matches: [] }) })),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("BrainFilterBar", () => {
  it("toggles node kinds and clears filters", () => {
    const setKinds = vi.fn();
    const clear = vi.fn();
    render(
      <ThemeProvider theme={keprixTheme}>
        <BrainFilterBar
          kinds={["memory", "skill"] as BrainNodeKind[]}
          setKinds={setKinds}
          range="all"
          setRange={vi.fn()}
          sessionId=""
          setSessionId={vi.fn()}
          query=""
          setQuery={vi.fn()}
          clear={clear}
          onResults={vi.fn()}
        />
      </ThemeProvider>,
    );

    fireEvent.click(screen.getByText("Memory"));
    expect(setKinds).toHaveBeenCalledWith(["skill"]);
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(clear).toHaveBeenCalled();
  });
});
