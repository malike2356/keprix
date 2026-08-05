import { describe, expect, it, vi } from "vitest";
import { fetchHomeBrainStats } from "@/lib/home-api";

vi.mock("@/lib/ce-api", () => ({
  ceApi: vi.fn(async (path: string) => {
    if (path === "/api/brain/graph/stats") {
      return {
        ok: true,
        json: async () => ({ nodes_by_kind: { memory: 4, skill: 2, document: 3, source: 1, tool: 5 } }),
      };
    }
    return { ok: false, json: async () => ({}) };
  }),
}));

describe("fetchHomeBrainStats", () => {
  it("prefers brain graph node counts", async () => {
    await expect(fetchHomeBrainStats()).resolves.toEqual({
      memoryCount: 4,
      skillCount: 2,
      documentCount: 3,
      sourceCount: 1,
      toolCount: 5,
    });
  });
});
