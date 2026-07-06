import { ceApi } from "@/lib/ce-api";

export type HubPack = {
  name: string;
  version: string;
  type: string;
  author: string;
  license: string;
  description?: string;
  risk_level: string;
  trust_label: string;
  review_score?: number | null;
  installed: boolean;
  enabled: boolean;
  source: string;
};

export async function fetchHubCatalog(): Promise<{
  packs: HubPack[];
  templates: HubPack[];
  connectors: HubPack[];
}> {
  const response = await ceApi("/api/hub/packs");
  if (!response.ok) throw new Error("Failed to load hub catalog");
  return response.json();
}

export async function installHubPack(
  name: string,
  approved = false,
): Promise<{ status: string; message?: string; gate_required?: boolean; gate_record_id?: string; sign_off_url?: string }> {
  const response = await ceApi("/api/hub/install", {
    method: "POST",
    body: JSON.stringify({ name, approved }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok && response.status !== 202) {
    throw new Error((payload as { detail?: string; error?: string }).detail || (payload as { error?: string }).error || "Install failed");
  }
  return payload;
}
