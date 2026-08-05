import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";
import type { BrainHealthReport } from "@/types/brain-health";

async function readHealthError(response: Response): Promise<Error> {
  let detail = "Failed to load brain health report";
  try {
    const payload = await response.json();
    detail = parseApiErrorMessage(payload, detail);
  } catch {
    // keep default
  }
  if (response.status === 401) {
    detail = `${detail}. Sign in again, then refresh.`;
  }
  return new Error(detail);
}

export async function fetchBrainHealth(refresh = false): Promise<BrainHealthReport> {
  const query = refresh ? "?refresh=true" : "";
  const response = await ceApi(`/api/brain/health${query}`);
  if (!response.ok) {
    throw await readHealthError(response);
  }
  return (await response.json()) as BrainHealthReport;
}

export async function deleteOrphanNodes(): Promise<number> {
  const response = await ceApi("/api/brain/health/delete-orphans", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm: true }),
  });
  if (!response.ok) throw new Error("Failed to delete orphan nodes");
  const payload = (await response.json()) as { deleted: number };
  return payload.deleted;
}

export async function mergeDuplicateNodes(keepId: string, deleteId: string): Promise<void> {
  const response = await ceApi("/api/brain/health/merge-duplicates", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keep_id: keepId, delete_id: deleteId }),
  });
  if (!response.ok) throw new Error("Failed to merge duplicate memories");
}

export async function archiveStaleNodes(nodeIds: string[], nodeKind = "memory"): Promise<number> {
  const response = await ceApi("/api/brain/health/archive-stale", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm: true, node_ids: nodeIds, node_kind: nodeKind }),
  });
  if (!response.ok) throw new Error("Failed to archive stale nodes");
  const payload = (await response.json()) as { archived: number };
  return payload.archived;
}
