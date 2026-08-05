import { ceApi } from "@/lib/ce-api";

async function downloadResponse(response: Response, fallbackName: string): Promise<void> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const message = typeof payload.detail === "string" ? payload.detail : "Export failed";
    throw new Error(message);
  }
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match?.[1] || fallbackName;
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export async function downloadBrainJsonExport(workspaceId?: string): Promise<void> {
  const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
  const response = await ceApi(`/api/brain/export/json${query}`);
  await downloadResponse(response, "brain-export.json");
}

export async function downloadBrainObsidianExport(workspaceId?: string): Promise<void> {
  const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
  const response = await ceApi(`/api/brain/export/obsidian${query}`);
  await downloadResponse(response, "brain-obsidian.zip");
}

export async function downloadBrainNodesCsv(workspaceId?: string): Promise<void> {
  const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
  const response = await ceApi(`/api/brain/export/csv${query}`);
  await downloadResponse(response, "brain-nodes.csv");
}

export async function downloadBrainEdgesCsv(workspaceId?: string): Promise<void> {
  const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
  const response = await ceApi(`/api/brain/export/csv/edges${query}`);
  await downloadResponse(response, "brain-edges.csv");
}
