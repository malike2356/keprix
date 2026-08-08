/** Client helpers for /api/admin/network-egress. */

import { ceApi } from "@/lib/ce-api";

export type EgressDecision = "ALLOWED" | "BLOCKED";

export type EgressEntry = {
  ts?: number;
  product_id?: string;
  host?: string;
  ip?: string;
  url_path?: string;
  decision?: EgressDecision | string;
  reason?: string;
  session_id?: string;
  tool_name?: string;
};

export type EgressAuditResponse = {
  count: number;
  entries: EgressEntry[];
};

export type EgressPolicySnapshot = {
  default_deny?: boolean;
  allowed_hosts?: string[];
  extra_denied_hosts?: string[];
  [key: string]: unknown;
};

export type EgressPolicyResponse = {
  products: string[];
  policies: Record<string, EgressPolicySnapshot>;
};

async function readJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    let detail = fallback;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export async function fetchEgressAudit(opts?: {
  n?: number;
  productId?: string;
  decision?: EgressDecision | "";
}): Promise<EgressAuditResponse> {
  const params = new URLSearchParams();
  params.set("n", String(opts?.n ?? 100));
  if (opts?.productId) params.set("product_id", opts.productId);
  if (opts?.decision) params.set("decision", opts.decision);
  const response = await ceApi(`/api/admin/network-egress?${params.toString()}`);
  return readJson(response, "Failed to load egress audit");
}

export async function fetchEgressPolicies(): Promise<EgressPolicyResponse> {
  const response = await ceApi("/api/admin/network-egress/policy");
  return readJson(response, "Failed to load egress policies");
}
