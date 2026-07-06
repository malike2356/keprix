import { ceApi } from "@/lib/ce-api";

export type LegalPolicy = {
  policy_type: string;
  version: string;
  title: string;
  summary: string;
  full_text_url: string;
};

export async function fetchLegalPolicies(): Promise<{ policies: LegalPolicy[] }> {
  const response = await ceApi("/api/legal/policies");
  if (!response.ok) throw new Error("Failed to load legal policies");
  return response.json();
}

export async function fetchLegalStatus(): Promise<{ pending: LegalPolicy[]; all_accepted: boolean }> {
  const response = await ceApi("/api/legal/status");
  if (!response.ok) throw new Error("Failed to load legal status");
  return response.json();
}

export async function acceptPolicies(policyTypes: string[]): Promise<void> {
  const response = await ceApi("/api/legal/accept", {
    method: "POST",
    body: JSON.stringify({ policy_types: policyTypes }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { error?: string }).error || "Acceptance failed");
  }
}
