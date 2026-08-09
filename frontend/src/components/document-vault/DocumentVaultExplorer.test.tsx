import { ThemeProvider } from "@mui/material/styles";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DocumentVaultExplorer from "@/components/document-vault/DocumentVaultExplorer";
import { keprixTheme } from "@/theme/keprix-theme";

const listVaultItems = vi.fn();
const createVaultItem = vi.fn();

vi.mock("@/lib/document-vault-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/document-vault-api")>(
    "@/lib/document-vault-api",
  );
  return {
    ...actual,
    listVaultItems: (...args: unknown[]) => listVaultItems(...args),
    createVaultItem: (...args: unknown[]) => createVaultItem(...args),
    getVaultContent: vi.fn(),
    importVaultFile: vi.fn(),
    exportVaultItem: vi.fn(),
    moveVaultItem: vi.fn(),
    patchVaultItem: vi.fn(),
    trashVaultItem: vi.fn(),
    restoreVaultItem: vi.fn(),
  };
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function renderExplorer() {
  return render(
    <ThemeProvider theme={keprixTheme}>
      <DocumentVaultExplorer />
    </ThemeProvider>,
  );
}

describe("DocumentVaultExplorer", () => {
  beforeEach(() => {
    listVaultItems.mockResolvedValue({
      workspace_id: "ws",
      items: [],
      count: 0,
      total: 0,
      limit: 100,
      offset: 0,
    });
  });

  it("shows empty state when vault has no items", async () => {
    renderExplorer();
    await waitFor(() => {
      expect(screen.getByText("Empty folder")).toBeTruthy();
    });
  });

  it("shows offline failure copy", async () => {
    listVaultItems.mockRejectedValue(Object.assign(new Error("failed to fetch"), { status: 0 }));
    renderExplorer();
    await waitFor(() => {
      expect(screen.getByText(/Offline/)).toBeTruthy();
    });
  });

  it("shows quota failure copy", async () => {
    listVaultItems.mockRejectedValue(
      Object.assign(new Error("too large"), { code: "quota_exceeded" }),
    );
    renderExplorer();
    await waitFor(() => {
      expect(screen.getByText(/Quota or size limit/)).toBeTruthy();
    });
  });

  it("shows conflict failure copy", async () => {
    listVaultItems.mockRejectedValue(Object.assign(new Error("conflict"), { status: 409 }));
    renderExplorer();
    await waitFor(() => {
      expect(screen.getByText(/Revision conflict/)).toBeTruthy();
    });
  });

  it("shows conversion failure copy", async () => {
    listVaultItems.mockRejectedValue(
      Object.assign(new Error("conversion"), { code: "unsupported_kind" }),
    );
    renderExplorer();
    await waitFor(() => {
      expect(screen.getByText(/Conversion failed/)).toBeTruthy();
    });
  });

  it("shows loading skeleton path then content", async () => {
    let resolveList: (value: unknown) => void = () => undefined;
    listVaultItems.mockReturnValue(
      new Promise((resolve) => {
        resolveList = resolve;
      }),
    );
    renderExplorer();
    expect(screen.getAllByText("Document Vault").length).toBeGreaterThan(0);
    resolveList({
      workspace_id: "ws",
      items: [{ id: "1", workspace_id: "ws", kind: "markdown", name: "Hello.md" }],
      count: 1,
      total: 1,
      limit: 100,
      offset: 0,
    });
    await waitFor(() => {
      expect(screen.getByText("Hello.md")).toBeTruthy();
    });
  });
});
