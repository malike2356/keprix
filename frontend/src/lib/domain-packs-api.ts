import { ceApi } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

export type DomainPack = {
  id: string;
  domain_name: string;
  version: string;
  jurisdictions: string[];
  source_quality_score: number;
  review_status: string;
  review_required: boolean;
  hub_published: boolean;
  status: string;
  disclaimers?: string[];
  limitations?: string[];
};

export async function fetchDomainPacks() {
  return parseJson<{ packs: DomainPack[]; count: number }>(
    await ceApi("/api/domain-packs"),
    "domain packs",
  );
}

export async function createDomainPack(domainName: string, jurisdictions: string[] = []) {
  return parseJson<{ pack: DomainPack }>(
    await ceApi("/api/domain-packs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domain_name: domainName, jurisdictions }),
    }),
    "create domain pack",
  );
}

export async function fetchDomainPack(packId: string) {
  return parseJson<{ pack: DomainPack }>(
    await ceApi(`/api/domain-packs/${encodeURIComponent(packId)}`),
    "domain pack",
  );
}

export async function validateDomainPack(packId: string, forPublish = false) {
  return parseJson<{ ok: boolean; errors: string[]; warnings: string[] }>(
    await ceApi(`/api/domain-packs/${encodeURIComponent(packId)}/validate?for_publish=${forPublish}`, {
      method: "POST",
    }),
    "validate domain pack",
  );
}

export async function publishDomainPack(packId: string, approved = false) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/domain-packs/${encodeURIComponent(packId)}/publish`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved }),
    }),
    "publish domain pack",
  );
}

export async function requestDomainPackReview(packId: string, summary: string) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/domain-packs/${encodeURIComponent(packId)}/review-request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ summary, reviewer_email: "reviewer@example.com", reviewer_name: "Reviewer" }),
    }),
    "domain pack review",
  );
}
