import { ceApi, getApiBaseUrl } from "@/lib/ce-api";
import type { BrainGraphData } from "@/types/brain-graph";

export type ShareScope = "all" | "memories_only" | "skills_only";

export type BrainShareLink = {
  share_id: string;
  created_at: string;
  expires_at: string | null;
  scope: ShareScope;
  access_count: number;
  last_accessed_at: string | null;
  password_protected: boolean;
  url?: string;
};

export type SharedBrainData = BrainGraphData & {
  title: string;
  scope: ShareScope;
  password_protected: boolean;
};

export async function listBrainShareLinks(workspaceId?: string): Promise<BrainShareLink[]> {
  const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
  const response = await ceApi(`/api/brain/share${query}`);
  if (!response.ok) throw new Error("Failed to load share links");
  const payload = (await response.json()) as { links: BrainShareLink[] };
  return payload.links;
}

export async function createBrainShareLink(body: {
  expires_in_days: number | null;
  scope: ShareScope;
  password?: string | null;
  workspaceId?: string;
}): Promise<BrainShareLink> {
  const query = body.workspaceId ? `?workspace_id=${encodeURIComponent(body.workspaceId)}` : "";
  const response = await ceApi(`/api/brain/share${query}`, {
    method: "POST",
    body: JSON.stringify({
      expires_in_days: body.expires_in_days,
      scope: body.scope,
      password: body.password || null,
    }),
  });
  if (!response.ok) throw new Error("Failed to create share link");
  return (await response.json()) as BrainShareLink;
}

export async function revokeBrainShareLink(shareId: string, workspaceId?: string): Promise<void> {
  const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
  const response = await ceApi(`/api/brain/share/${encodeURIComponent(shareId)}${query}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Failed to revoke share link");
}

export function sharePageUrl(shareId: string): string {
  if (typeof window !== "undefined") {
    return `${window.location.origin}/brain/share/${shareId}`;
  }
  return `/brain/share/${shareId}`;
}

export async function fetchSharedBrainData(shareId: string, password?: string | null): Promise<SharedBrainData> {
  const params = new URLSearchParams();
  if (password) params.set("password", password);
  const query = params.toString() ? `?${params.toString()}` : "";
  const base = getApiBaseUrl();
  const response = await fetch(`${base}/api/brain/share/${encodeURIComponent(shareId)}/data${query}`, {
    credentials: "include",
  });
  if (response.status === 401) {
    throw new Error("password_required");
  }
  if (response.status === 410) {
    throw new Error("expired");
  }
  if (!response.ok) {
    throw new Error("Share link not found");
  }
  return (await response.json()) as SharedBrainData;
}

export async function fetchSharedBrainNode(
  shareId: string,
  kind: string,
  id: string,
  password?: string | null,
) {
  const params = new URLSearchParams();
  if (password) params.set("password", password);
  const query = params.toString() ? `?${params.toString()}` : "";
  const base = getApiBaseUrl();
  const response = await fetch(
    `${base}/api/brain/share/${encodeURIComponent(shareId)}/node/${encodeURIComponent(kind)}/${encodeURIComponent(id)}${query}`,
    { credentials: "include" },
  );
  if (!response.ok) throw new Error("Failed to load node");
  return response.json();
}
