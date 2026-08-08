/** Client helpers for /api/admin/quotas and /api/quotas/status. */

import { ceApi } from "@/lib/ce-api";

export type ProductQuotaUsage = {
  product_id: string;
  period_start?: string;
  period_end?: string;
  usage?: Record<string, number>;
  limits?: Record<string, number>;
  burst_allowance?: number;
};

export type ProductQuotasResponse = {
  products: string[];
  usages: ProductQuotaUsage[];
  deployment_tier?: string;
  note?: string;
};

export type SchedulerStats = {
  active_slots: number;
  max_slots: number;
  queued_requests: number;
  per_product?: Record<string, number>;
};

export type ActorScopeType = "workspace" | "agent" | "api_token" | "user" | "product";

export type ActorQuotaStatus = {
  scope?: { type?: string; id?: string };
  period?: string;
  limits?: Record<string, unknown>;
  usage?: {
    calls?: number;
    tokens?: number;
    tool_runs?: number;
    mutation_runs?: number;
    per_service?: Record<string, Record<string, number>>;
  };
  remaining?: {
    calls?: number | null;
    tokens?: number | null;
    tool_runs?: number | null;
    mutation_runs?: number | null;
  };
  override?: Record<string, unknown> | null;
};

export type ActorDenial = {
  id?: number;
  created_at?: string;
  scope_type?: string;
  scope_id?: string;
  service?: string | null;
  metric?: string | null;
  reason?: string | null;
  workspace_id?: string | null;
  run_id?: string | null;
};

export type ActorOverrideLimits = {
  period?: "day" | "month";
  max_calls?: number;
  max_tokens?: number;
  max_tool_runs?: number;
  max_mutation_runs?: number;
};

async function readJson<T>(response: Response, fallbackError: string): Promise<T> {
  if (!response.ok) {
    let detail = fallbackError;
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

export async function fetchProductQuotas(): Promise<ProductQuotasResponse> {
  const response = await ceApi("/api/admin/quotas");
  return readJson(response, "Failed to load product quotas");
}

export async function fetchProductQuota(productId: string): Promise<{
  product_id: string;
  period?: string;
  burst_allowance?: number;
  usage?: ProductQuotaUsage;
}> {
  const response = await ceApi(`/api/admin/quotas/${encodeURIComponent(productId)}`);
  return readJson(response, `Failed to load quota for ${productId}`);
}

export async function resetProductQuota(productId: string): Promise<{ product_id: string; status: string }> {
  const response = await ceApi(`/api/admin/quotas/${encodeURIComponent(productId)}/reset`, {
    method: "POST",
  });
  return readJson(response, `Failed to reset quota for ${productId}`);
}

export async function fetchSchedulerStats(): Promise<SchedulerStats> {
  const response = await ceApi("/api/admin/quotas/scheduler");
  return readJson(response, "Failed to load scheduler stats");
}

export async function fetchActorDenials(limit = 50): Promise<{ items: ActorDenial[] }> {
  const response = await ceApi(`/api/admin/quotas/actors/denials?limit=${limit}`);
  return readJson(response, "Failed to load quota denials");
}

export async function fetchActorQuota(
  scopeType: ActorScopeType,
  scopeId: string,
): Promise<ActorQuotaStatus> {
  const response = await ceApi(
    `/api/admin/quotas/actors/${encodeURIComponent(scopeType)}/${encodeURIComponent(scopeId)}`,
  );
  return readJson(response, "Failed to load actor quota");
}

export async function putActorQuotaOverride(
  scopeType: ActorScopeType,
  scopeId: string,
  limits: ActorOverrideLimits | null,
): Promise<{ scope: Record<string, unknown>; limits: Record<string, unknown> | null }> {
  const response = await ceApi(
    `/api/admin/quotas/actors/${encodeURIComponent(scopeType)}/${encodeURIComponent(scopeId)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limits }),
    },
  );
  return readJson(response, "Failed to save actor quota override");
}

export async function fetchUserQuotaStatus(): Promise<{
  deployment_tier?: string;
  note?: string;
  user?: ActorQuotaStatus;
  workspace?: ActorQuotaStatus;
}> {
  const response = await ceApi("/api/quotas/status");
  return readJson(response, "Failed to load your quota status");
}

export function formatResourceLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function usagePercent(used: number, limit: number): number | null {
  if (!limit || limit <= 0) return null;
  if (limit >= 1_000_000_000) return null; // treat as effectively unlimited for UI
  return Math.min(100, Math.round((used / limit) * 100));
}

export function formatCount(value: number | null | undefined): string {
  if (value == null) return "Unlimited";
  if (value >= 1_000_000_000) return "Unlimited";
  return new Intl.NumberFormat().format(value);
}
