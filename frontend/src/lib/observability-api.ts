import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type ObservabilityUsageSummary = {
  request_count?: number;
  total_tokens?: number;
  total_cost_usd?: number;
};

export type ObservabilityRuntimeHealth = {
  trace_volume?: number;
  error_count?: number;
  error_rate?: number;
  latency_avg_ms?: number | null;
  latency_p95_ms?: number | null;
  otel_configured?: boolean;
};

export type ObservabilityDashboard = {
  cost: Record<string, unknown>;
  tokens: Record<string, unknown>;
  trace_count: number;
  otel_configured: boolean;
  usage_summary: ObservabilityUsageSummary | null;
  runtime?: ObservabilityRuntimeHealth | null;
};

export type ObservabilitySpan = {
  kind: string;
  name: string;
  offset_ms: number;
  duration_ms: number;
  detail?: unknown;
};

export type ObservabilityTrace = {
  run_id?: string;
  id?: string;
  workspace_id?: string;
  user_request?: string;
  agent_roles?: string[];
  outcome?: string;
  status?: string;
  agent?: string;
  summary?: string;
  started_at?: string;
  finished_at?: string | null;
  duration_ms?: number;
  cost_estimate_usd?: number;
  tokens?: Record<string, number>;
  node_transitions?: unknown[];
  tool_calls?: unknown[];
  model_calls?: unknown[];
  errors?: unknown[];
  spans?: ObservabilitySpan[];
  [key: string]: unknown;
};

export type ObservabilityTraceFilters = {
  limit?: number;
  status?: string;
  agent?: string;
  q?: string;
  since?: string;
  until?: string;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return payload as T;
}

function buildTraceQuery(filters?: ObservabilityTraceFilters): string {
  const search = new URLSearchParams();
  if (filters?.limit != null) search.set("limit", String(filters.limit));
  if (filters?.status) search.set("status", filters.status);
  if (filters?.agent) search.set("agent", filters.agent);
  if (filters?.q) search.set("q", filters.q);
  if (filters?.since) search.set("since", filters.since);
  if (filters?.until) search.set("until", filters.until);
  const query = search.toString();
  return query ? `?${query}` : "";
}

export async function fetchObservabilityDashboard(): Promise<ObservabilityDashboard> {
  return parseJson(await ceApi("/api/observability/dashboard"), "Failed to load observability dashboard");
}

export async function fetchObservabilityTraces(
  limitOrFilters: number | ObservabilityTraceFilters = 50,
): Promise<ObservabilityTrace[]> {
  const filters: ObservabilityTraceFilters =
    typeof limitOrFilters === "number" ? { limit: limitOrFilters } : limitOrFilters;
  const data = await parseJson<{ traces: ObservabilityTrace[] }>(
    await ceApi(`/api/observability/traces${buildTraceQuery(filters)}`),
    "Failed to load traces",
  );
  return data.traces || [];
}

export async function fetchObservabilityTrace(runId: string): Promise<ObservabilityTrace> {
  return parseJson(
    await ceApi(`/api/observability/traces/${encodeURIComponent(runId)}`),
    "Failed to load trace",
  );
}

export async function exportObservabilityTrace(runId: string): Promise<{
  otel: Record<string, unknown>;
  governance: Record<string, unknown>;
}> {
  return parseJson(
    await ceApi(`/api/observability/traces/${encodeURIComponent(runId)}/export`, { method: "POST" }),
    "Failed to export trace",
  );
}
