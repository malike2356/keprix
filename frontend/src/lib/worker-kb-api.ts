import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const raw = search.toString();
  return raw ? `?${raw}` : "";
}

export type WorkerKbEntry = {
  id: string;
  title?: string | null;
  content?: string;
  entry_type?: string;
  enabled?: boolean | number;
  source?: string | null;
  created_at?: string;
};

export async function fetchWorkerKbEntries(workerId: string, workspaceId = "default") {
  return parseJson<{ entries: WorkerKbEntry[]; count: number; knowledge_base: Record<string, unknown> }>(
    await ceApi(
      `/api/worker-kb/entries${qs({ workspace_id: workspaceId, worker_id: workerId })}`,
    ),
    "Failed to load worker knowledge base",
  );
}

export async function addWorkerKbEntry(input: {
  workerId: string;
  content: string;
  title?: string;
  entryType?: string;
  workspaceId?: string;
}) {
  return parseJson<{ entry: WorkerKbEntry }>(
    await ceApi(`/api/worker-kb/entries${qs({ workspace_id: input.workspaceId || "default" })}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        worker_id: input.workerId,
        content: input.content,
        title: input.title,
        entry_type: input.entryType || "faq",
      }),
    }),
    "Failed to add knowledge entry",
  );
}

export async function toggleWorkerKbEntry(
  entryId: string,
  workerId: string,
  enabled?: boolean,
  workspaceId = "default",
) {
  return parseJson<{ entry: WorkerKbEntry }>(
    await ceApi(`/api/worker-kb/entries/${encodeURIComponent(entryId)}/toggle${qs({ workspace_id: workspaceId })}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ worker_id: workerId, enabled }),
    }),
    "Failed to toggle entry",
  );
}

export async function deleteWorkerKbEntry(entryId: string, workerId: string, workspaceId = "default") {
  return parseJson<{ deleted: boolean }>(
    await ceApi(
      `/api/worker-kb/entries/${encodeURIComponent(entryId)}${qs({ workspace_id: workspaceId, worker_id: workerId })}`,
      { method: "DELETE" },
    ),
    "Failed to delete entry",
  );
}

export async function searchWorkerKb(workerId: string, query: string, workspaceId = "default") {
  return parseJson<{ results: Array<Record<string, unknown>> }>(
    await ceApi(`/api/worker-kb/search${qs({ workspace_id: workspaceId })}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ worker_id: workerId, query, limit: 8 }),
    }),
    "Failed to search knowledge base",
  );
}
