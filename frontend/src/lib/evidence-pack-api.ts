import { ceApi } from "@/lib/ce-api";

export type EvidencePackRecord = {
  pack_id: string;
  workspace_id: string;
  status: string;
  date_from: string;
  date_to: string;
  event_count: number;
  document_count: number;
  generated_at: string;
  download_url?: string;
  scout_submission_id?: string | null;
  scout_pack_url?: string | null;
};

export async function listEvidencePacks(): Promise<EvidencePackRecord[]> {
  const response = await ceApi("/api/evidence-pack");
  if (!response.ok) {
    throw new Error("Failed to load evidence packs");
  }
  const body = await response.json();
  return body.packs ?? [];
}

export async function generateEvidencePack(input: {
  date_from: string;
  date_to: string;
  event_types?: string[];
  include_documents?: boolean;
  domain_pack?: string;
}): Promise<{ pack_id: string; status: string }> {
  const response = await ceApi("/api/evidence-pack/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to generate evidence pack");
  }
  return response.json();
}

export async function sendEvidencePackToProvider(packId: string): Promise<{
  provider_submission_id: string;
  provider_pack_url: string;
}> {
  const response = await ceApi(`/api/evidence-pack/${packId}/send-to-provider`, {
    method: "POST",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to send evidence pack to governance provider");
  }
  const payload = await response.json();
  return {
    provider_submission_id: String(payload.provider_submission_id ?? ""),
    provider_pack_url: String(payload.provider_pack_url ?? ""),
  };
}

/** @deprecated Use sendEvidencePackToProvider */
export async function sendEvidencePackToScout(packId: string): Promise<{
  scout_submission_id: string;
  scout_pack_url: string;
}> {
  const result = await sendEvidencePackToProvider(packId);
  return {
    scout_submission_id: result.provider_submission_id,
    scout_pack_url: result.provider_pack_url,
  };
}
