import type { KeprixClient } from "./client.js";

export class RagApi {
  constructor(private readonly client: KeprixClient) {}

  async ingest(sourceId: string, content: string, sourceType = "plaintext") {
    return this.client.request<{ ok: boolean; chunks: number }>("/api/rag/ingest", {
      method: "POST",
      body: JSON.stringify({ source_id: sourceId, content, source_type: sourceType }),
    });
  }

  async search(query: string, limit = 5, hybrid = true) {
    return this.client.request<{ results: unknown[] }>("/api/rag/search", {
      method: "POST",
      body: JSON.stringify({ query, limit, hybrid }),
    });
  }

  async listSources() {
    return this.client.request<{ sources: unknown[] }>("/api/rag/sources");
  }

  async queryDocuments(question: string, indexId?: string, evidenceFirst = true) {
    return this.client.request<Record<string, unknown>>("/api/documents/query", {
      method: "POST",
      body: JSON.stringify({
        user_id: this.client.userId,
        question,
        index_id: indexId,
        evidence_first: evidenceFirst,
      }),
    });
  }
}
