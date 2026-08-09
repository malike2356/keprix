/** Document Vault HTTP client (Prompt 648). Tenant vault only; never host FS. */

import { ceApi, getCEUser } from "@/lib/ce-api";

export type VaultItem = {
  id: string;
  workspace_id: string;
  parent_id?: string | null;
  kind: string;
  name: string;
  mime_type?: string;
  extension?: string;
  current_revision?: number;
  checksum?: string | null;
  byte_size?: number;
  is_favorite?: boolean;
  trashed_at?: string | null;
  trashed?: boolean;
  metadata?: Record<string, unknown>;
  updated_at?: string;
  created_at?: string;
};

export type VaultListResult = {
  workspace_id: string;
  parent_id?: string | null;
  items: VaultItem[];
  count: number;
  total: number;
  limit: number;
  offset: number;
};

export type VaultErrorState =
  | "offline"
  | "empty"
  | "loading"
  | "quota"
  | "conflict"
  | "conversion"
  | "forbidden"
  | "unknown";

function workspaceHeader(): HeadersInit {
  const user = getCEUser();
  const ws = user?.active_workspace_id || user?.workspace_id || user?.id || "";
  return ws ? { "X-Workspace-Id": ws } : {};
}

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = (payload as { detail?: unknown }).detail;
    let message = fallback;
    let code = "";
    if (typeof detail === "string") {
      message = detail;
    } else if (detail && typeof detail === "object") {
      const d = detail as { message?: string; error_code?: string };
      message = d.message || d.error_code || fallback;
      code = d.error_code || "";
    }
    const err = new Error(message) as Error & { status?: number; code?: string };
    err.status = response.status;
    err.code = code;
    throw err;
  }
  return response.json() as Promise<T>;
}

export function classifyVaultError(error: unknown): VaultErrorState {
  if (typeof navigator !== "undefined" && !navigator.onLine) return "offline";
  const err = error as { status?: number; code?: string; message?: string };
  const code = (err.code || "").toLowerCase();
  const msg = (err.message || "").toLowerCase();
  if (err.status === 0 || msg.includes("failed to fetch") || msg.includes("network")) return "offline";
  if (code === "quota_exceeded" || msg.includes("quota") || msg.includes("too large")) return "quota";
  if (code === "stale_revision" || code === "conflict" || err.status === 409) return "conflict";
  if (code === "not_configured" || code === "unsupported_kind" || msg.includes("conversion")) return "conversion";
  if (err.status === 403 || code === "host_fs_forbidden" || code === "workspace_mismatch") return "forbidden";
  return "unknown";
}

export async function listVaultItems(opts?: {
  parentId?: string | null;
  q?: string;
  includeTrashed?: boolean;
  limit?: number;
}): Promise<VaultListResult> {
  const params = new URLSearchParams();
  if (opts?.parentId) params.set("parent_id", opts.parentId);
  if (opts?.q) params.set("q", opts.q);
  if (opts?.includeTrashed) params.set("include_trashed", "true");
  if (opts?.limit) params.set("limit", String(opts.limit));
  const qs = params.toString();
  return parseJson<VaultListResult>(
    await ceApi(`/api/document-vault/items${qs ? `?${qs}` : ""}`, {
      headers: workspaceHeader(),
    }),
    "Failed to list vault items",
  );
}

export async function getVaultItem(itemId: string): Promise<VaultItem> {
  return parseJson<VaultItem>(
    await ceApi(`/api/document-vault/items/${encodeURIComponent(itemId)}`, {
      headers: workspaceHeader(),
    }),
    "Failed to load vault item",
  );
}

export async function getVaultContent(itemId: string): Promise<{ item_id: string; content: string }> {
  return parseJson(
    await ceApi(`/api/document-vault/items/${encodeURIComponent(itemId)}/content`, {
      headers: workspaceHeader(),
    }),
    "Failed to load content",
  );
}

export async function createVaultItem(body: {
  kind: string;
  name: string;
  parent_id?: string | null;
  content?: string;
}): Promise<VaultItem> {
  return parseJson<VaultItem>(
    await ceApi("/api/document-vault/items", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...workspaceHeader() },
      body: JSON.stringify(body),
    }),
    "Failed to create item",
  );
}

export async function patchVaultItem(
  itemId: string,
  body: Record<string, unknown>,
): Promise<VaultItem> {
  return parseJson<VaultItem>(
    await ceApi(`/api/document-vault/items/${encodeURIComponent(itemId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...workspaceHeader() },
      body: JSON.stringify(body),
    }),
    "Failed to update item",
  );
}

export async function moveVaultItem(itemId: string, parentId: string | null): Promise<VaultItem> {
  return parseJson<VaultItem>(
    await ceApi(`/api/document-vault/items/${encodeURIComponent(itemId)}/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...workspaceHeader() },
      body: JSON.stringify({ parent_id: parentId }),
    }),
    "Failed to move item",
  );
}

export async function trashVaultItem(itemId: string): Promise<VaultItem> {
  return parseJson<VaultItem>(
    await ceApi(`/api/document-vault/items/${encodeURIComponent(itemId)}/trash`, {
      method: "POST",
      headers: workspaceHeader(),
    }),
    "Failed to trash item",
  );
}

export async function restoreVaultItem(itemId: string): Promise<VaultItem> {
  return parseJson<VaultItem>(
    await ceApi(`/api/document-vault/items/${encodeURIComponent(itemId)}/restore`, {
      method: "POST",
      headers: workspaceHeader(),
    }),
    "Failed to restore item",
  );
}

export async function importVaultFile(file: File, parentId?: string | null): Promise<unknown> {
  const form = new FormData();
  form.append("file", file);
  const params = new URLSearchParams();
  if (parentId) params.set("parent_id", parentId);
  const qs = params.toString();
  return parseJson(
    await ceApi(`/api/document-vault/import${qs ? `?${qs}` : ""}`, {
      method: "POST",
      headers: workspaceHeader(),
      body: form,
    }),
    "Failed to import file",
  );
}

export async function exportVaultItem(itemId: string, format: string): Promise<Blob> {
  const response = await ceApi(`/api/document-vault/items/${encodeURIComponent(itemId)}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...workspaceHeader() },
    body: JSON.stringify({ format }),
  });
  if (!response.ok) {
    await parseJson(response, "Failed to export");
  }
  return response.blob();
}

export async function fetchVaultFormats(): Promise<unknown> {
  return parseJson(
    await ceApi("/api/document-vault/formats", { headers: workspaceHeader() }),
    "Failed to load formats",
  );
}

export async function fetchGoogleDriveStatus(): Promise<Record<string, unknown>> {
  return parseJson(
    await ceApi("/api/document-vault/google/status", { headers: workspaceHeader() }),
    "Failed to load Google Drive status",
  );
}

export async function syncGoogleDrive(body?: {
  direction?: string;
  item_id?: string;
  source?: string;
}): Promise<Record<string, unknown>> {
  return parseJson(
    await ceApi("/api/document-vault/google/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...workspaceHeader() },
      body: JSON.stringify(body || { direction: "inbound", source: "manual" }),
    }),
    "Failed to sync Google Drive",
  );
}

export async function fetchGoogleDriveConflicts(): Promise<{ conflicts: unknown[] }> {
  return parseJson(
    await ceApi("/api/document-vault/google/conflicts", { headers: workspaceHeader() }),
    "Failed to load conflicts",
  );
}

export async function resolveGoogleDriveConflict(
  itemId: string,
  choice: "keep_local" | "keep_remote" | "keep_both",
): Promise<Record<string, unknown>> {
  return parseJson(
    await ceApi(`/api/document-vault/google/conflicts/${encodeURIComponent(itemId)}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...workspaceHeader() },
      body: JSON.stringify({ choice }),
    }),
    "Failed to resolve conflict",
  );
}
