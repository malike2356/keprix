import { describe, expect, it, vi } from "vitest";
import { EmbeddingClient } from "../src/embedding-client";

describe("EmbeddingClient", () => {
  it("posts search requests to the ML service", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ results: [] }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const client = new EmbeddingClient("http://ml.test");
    await expect(client.search({ query: "water", pack_id: "borehole" })).resolves.toEqual({ results: [] });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://ml.test/embeddings/search",
      expect.objectContaining({ method: "POST" }),
    );

    vi.unstubAllGlobals();
  });
});
