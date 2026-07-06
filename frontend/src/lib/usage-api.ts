import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type UsageQueryParams = {
  days?: number;
  workspace_id?: string;
  channel?: string;
  model?: string;
  provider?: string;
};

export type UsageSummary = {
  period_days: number;
  request_count: number;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  total_cost_usd: number;
  estimated_cost_usd: number;
  unknown_cost_count: number;
  avg_cost_per_request_usd: number;
  avg_tokens_per_request: number;
};

export type UsageTimeseriesPoint = {
  date: string;
  request_count: number;
  total_tokens: number;
  total_cost_usd: number;
};

export type UsageBreakdownRow = {
  key: string;
  label: string;
  request_count: number;
  total_tokens: number;
  total_cost_usd: number;
  share_percent: number;
};

export type UsageEventRow = {
  id: string;
  recorded_at: string;
  user_id?: string | null;
  session_id?: string | null;
  channel: string;
  provider: string;
  model: string;
  total_tokens: number;
  cost_usd?: number | null;
  cost_status: string;
};

export type UsageBudgetStatus = {
  workspace_id: string;
  spent_usd: number;
  monthly_budget_usd: number | null;
  alert_threshold_percent: number;
  percent_used: number | null;
  alert: boolean;
  month_start_utc: string;
};

function buildQuery(params?: UsageQueryParams): string {
  const search = new URLSearchParams();
  if (params?.days !== undefined) {
    search.set("days", String(params.days));
  }
  if (params?.workspace_id) {
    search.set("workspace_id", params.workspace_id);
  }
  if (params?.channel) {
    search.set("channel", params.channel);
  }
  if (params?.model) {
    search.set("model", params.model);
  }
  if (params?.provider) {
    search.set("provider", params.provider);
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
}

export async function fetchUsageSummary(params?: UsageQueryParams): Promise<UsageSummary> {
  const response = await ceApi(`/api/usage/summary${buildQuery(params)}`);
  return parseJson(response, "Failed to load usage summary");
}

export async function fetchUsageTimeseries(
  params?: UsageQueryParams & { granularity?: "day" | "hour" },
): Promise<UsageTimeseriesPoint[]> {
  const search = new URLSearchParams(buildQuery(params).replace(/^\?/, ""));
  if (params?.granularity) {
    search.set("granularity", params.granularity);
  }
  const query = search.toString();
  const response = await ceApi(`/api/usage/timeseries${query ? `?${query}` : ""}`);
  const payload = await parseJson<{ points: UsageTimeseriesPoint[] }>(response, "Failed to load usage timeseries");
  return payload.points ?? [];
}

export async function fetchUsageBreakdown(
  dimension: "model" | "provider" | "channel" | "user",
  params?: UsageQueryParams,
): Promise<UsageBreakdownRow[]> {
  const response = await ceApi(`/api/usage/breakdown/${dimension}${buildQuery(params)}`);
  const payload = await parseJson<{ items: UsageBreakdownRow[] }>(
    response,
    "Failed to load usage breakdown",
  );
  return payload.items ?? [];
}

export async function fetchUsageEvents(
  params?: UsageQueryParams & { limit?: number; offset?: number },
): Promise<{ items: UsageEventRow[]; total: number }> {
  const search = new URLSearchParams(buildQuery(params).replace(/^\?/, ""));
  if (params?.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  if (params?.offset !== undefined) {
    search.set("offset", String(params.offset));
  }
  const query = search.toString();
  const response = await ceApi(`/api/usage/events${query ? `?${query}` : ""}`);
  return parseJson(response, "Failed to load usage events");
}

export async function fetchUsageBudget(workspaceId = "default"): Promise<UsageBudgetStatus> {
  const response = await ceApi(`/api/usage/budget?workspace_id=${encodeURIComponent(workspaceId)}`);
  return parseJson(response, "Failed to load usage budget");
}

export async function updateUsageBudget(body: {
  monthly_budget_usd: number | null;
  alert_threshold_percent: number;
}): Promise<{ budget: Record<string, unknown>; status: UsageBudgetStatus }> {
  const response = await ceApi("/api/usage/budget", {
    method: "PUT",
    body: JSON.stringify(body),
  });
  return parseJson(response, "Failed to update usage budget");
}

export async function downloadUsageExport(days = 90): Promise<void> {
  const response = await ceApi(`/api/usage/export?days=${days}`);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Failed to export usage CSV"));
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "llm-usage-export.csv";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export const USAGE_PERIOD_STORAGE_KEY = "keprix-usage-period-days";

export const USAGE_PERIOD_OPTIONS = [7, 30, 90] as const;

export type UsagePeriodDays = (typeof USAGE_PERIOD_OPTIONS)[number];

export function readStoredUsagePeriod(): UsagePeriodDays {
  if (typeof window === "undefined") {
    return 30;
  }
  const raw = localStorage.getItem(USAGE_PERIOD_STORAGE_KEY);
  const parsed = raw ? Number(raw) : 30;
  return USAGE_PERIOD_OPTIONS.includes(parsed as UsagePeriodDays) ? (parsed as UsagePeriodDays) : 30;
}

export function storeUsagePeriod(days: UsagePeriodDays): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.setItem(USAGE_PERIOD_STORAGE_KEY, String(days));
}
