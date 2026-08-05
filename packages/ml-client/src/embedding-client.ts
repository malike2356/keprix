import { MLServiceClientBase } from "./base-client";
import type { EmbedRequest, EmbedResponse, KnowledgePack, SearchRequest, SearchResult } from "./types";

export class EmbeddingClient extends MLServiceClientBase {
  embed(request: EmbedRequest): Promise<EmbedResponse> {
    return this.post<EmbedResponse>("/embeddings/embed", request);
  }

  search(request: SearchRequest): Promise<{ results: SearchResult[] }> {
    return this.post<{ results: SearchResult[] }>("/embeddings/search", request);
  }

  ingest(
    packId: string,
    sourceUri: string,
    content: string,
    metadata: Record<string, unknown> = {},
  ): Promise<{ pack_id: string; source_uri: string; chunks_stored: number }> {
    return this.post("/embeddings/ingest", {
      pack_id: packId,
      source_uri: sourceUri,
      content,
      metadata,
    });
  }

  createPack(packId: string, displayName: string, description = ""): Promise<{ pack_id: string; status: string }> {
    return this.post("/embeddings/packs", {
      pack_id: packId,
      display_name: displayName,
      description,
    });
  }

  async listPacks(): Promise<KnowledgePack[]> {
    const response = await fetch(`${this.baseUrl}/embeddings/packs`);
    if (!response.ok) {
      throw new Error(`ML service error ${response.status}: ${await response.text()}`);
    }
    const data = (await response.json()) as { packs: KnowledgePack[] };
    return data.packs;
  }

  async deletePack(packId: string): Promise<{ pack_id: string; status: string }> {
    const response = await fetch(`${this.baseUrl}/embeddings/packs/${encodeURIComponent(packId)}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error(`ML service error ${response.status}: ${await response.text()}`);
    }
    return response.json() as Promise<{ pack_id: string; status: string }>;
  }
}
