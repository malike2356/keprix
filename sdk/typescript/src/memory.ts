import type { KeprixClient } from "./client.js";

export type MemoryRecord = {
  id: string;
  content: string;
  metadata?: Record<string, unknown>;
};

export class MemoryApi {
  constructor(private readonly client: KeprixClient) {}

  async listConversationHistory(sessionId?: string) {
    if (sessionId) {
      return this.client.request<{ id: string; messages: unknown[] }>(`/api/conversations/${sessionId}`);
    }
    return this.client.request<{ conversations: unknown[] }>("/api/conversations");
  }

  async saveObservational(content: string, tags: string[] = [], sessionId?: string) {
    return this.client.request<{ ok: boolean; memory_id: string }>("/api/memory/save", {
      method: "POST",
      body: JSON.stringify({ content, tags, session_id: sessionId }),
    });
  }

  async searchObservational(query: string, limit = 10) {
    return this.client.request<{ results: MemoryRecord[] }>("/api/memory/search", {
      method: "POST",
      body: JSON.stringify({ query, limit }),
    });
  }

  async searchRetrieval(query: string, limit = 5, hybrid = true) {
    return this.client.request<{ results: unknown[] }>("/api/rag/search", {
      method: "POST",
      body: JSON.stringify({ query, limit, hybrid }),
    });
  }

  async saveWorkspaceFact(content: string) {
    return this.saveObservational(content, ["workspace_fact"]);
  }

  async listWorkspaceFacts() {
    const payload = await this.client.request<{ memories: MemoryRecord[] }>("/api/memory/list");
    return (payload.memories || []).filter((row) =>
      (row.metadata?.tags as string[] | undefined)?.includes("workspace_fact"),
    );
  }

  async saveUserPreference(key: string, value: string) {
    return this.saveObservational(`${key}=${value}`, ["user_preference", key]);
  }

  async listUserPreferences() {
    const payload = await this.client.request<{ memories: MemoryRecord[] }>("/api/memory/list");
    return (payload.memories || []).filter((row) =>
      (row.metadata?.tags as string[] | undefined)?.includes("user_preference"),
    );
  }
}
