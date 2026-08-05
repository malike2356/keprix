import { ThemeProvider } from "@mui/material/styles";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import NodeContentPanel from "@/components/brain/NodeContentPanel";
import { keprixTheme } from "@/theme/keprix-theme";
import type { GraphNode } from "@/types/brain-graph";

vi.mock("@/lib/ce-api", () => ({
  ceApi: vi.fn(async (path: string) => {
    if (path.includes("/neighbours/")) {
      return {
        ok: true,
        json: async () => ({ nodes: [], edges: [], total_nodes: 0, total_edges: 0, truncated: false }),
      };
    }
    return {
      ok: true,
      json: async () => ({
        id: "calendar_book",
        kind: "tool",
        label: "Calendar Book",
        summary: "Book calendar appointments.",
        created_at: "2026-07-09T10:00:00Z",
        updated_at: null,
        metadata: { registry: "builtin" },
        deleted: false,
        content: { id: "calendar_book" },
      }),
    };
  }),
}));

const toolNode: GraphNode = {
  id: "calendar_book",
  kind: "tool",
  label: "Calendar Book",
  summary: "Book calendar appointments.",
  created_at: "2026-07-09T10:00:00Z",
  updated_at: null,
  metadata: {},
  deleted: false,
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("NodeContentPanel", () => {
  it("renders selected node content and keeps tools read-only", async () => {
    render(
      <ThemeProvider theme={keprixTheme}>
        <NodeContentPanel node={toolNode} onClose={vi.fn()} />
      </ThemeProvider>,
    );

    expect(screen.getByText("Calendar Book")).toBeInTheDocument();
    expect(await screen.findByText("Book calendar appointments.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.getByText("Connected to (0)")).toBeInTheDocument();
  });
});
