import { afterEach, describe, expect, it, vi } from "vitest";
import {
  GRID_PREFS_KEY,
  leadStatusKinds,
  loadLeadGridPrefs,
  saveLeadGridPrefs,
  statusChipLabel,
} from "@/components/crm/leadGridStatus";
import type { CrmRecord } from "@/components/crm/types";

afterEach(() => {
  window.localStorage.clear();
  vi.clearAllMocks();
});

describe("leadGridStatus helpers", () => {
  it("detects missing and invalid email statuses", () => {
    expect(leadStatusKinds({ id: "1" } as CrmRecord)).toContain("missing_email");
    expect(leadStatusKinds({ id: "2", emails: [{ address: "bad" }] } as CrmRecord)).toContain(
      "invalid_email",
    );
    expect(leadStatusKinds({ id: "3", emails: [{ address: "ok@example.com" }], stage: "booked" } as CrmRecord)).toContain(
      "booked",
    );
    expect(statusChipLabel("customer")).toBe("Customer");
  });

  it("persists column prefs to localStorage", () => {
    saveLeadGridPrefs({
      density: "compact",
      columnVisibilityModel: { notes: false },
      columnOrder: ["company_name", "name"],
      columnWidths: { company_name: 200 },
    });
    const raw = window.localStorage.getItem(GRID_PREFS_KEY);
    expect(raw).toBeTruthy();
    const loaded = loadLeadGridPrefs();
    expect(loaded.density).toBe("compact");
    expect(loaded.columnVisibilityModel?.notes).toBe(false);
    expect(loaded.columnWidths?.company_name).toBe(200);
  });
});
