import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type AnalyticsPeriodDays = 7 | 30 | 90;

export type AivaAnalyticsOverview = {
  workspace_id: string;
  days: number;
  agent: {
    calls: number;
    tokens: number;
    errors: number;
    avg_duration_seconds: number;
    estimated_cost_usd: number;
    tool_calls: number;
  };
  outreach: {
    emails_sent: number;
    replies: number;
    bookings: number;
    reply_rate: number;
    booking_rate: number;
  };
  workers: {
    messages: number;
    escalations: number;
  };
};

export type AivaAnalyticsUsage = {
  workspace_id: string;
  days: number;
  series: Array<{
    day: string;
    agent_calls: number;
    tokens: number;
    cost_usd: number;
    emails_sent: number;
    replies: number;
    worker_messages: number;
  }>;
  totals: {
    agent_calls: number;
    tokens: number;
    cost_usd: number;
    emails_sent: number;
    replies: number;
    worker_messages: number;
  };
};

export type AivaAnalyticsOutreach = {
  workspace_id: string;
  campaign_id?: string | null;
  days: number;
  funnel: {
    emails_sent: number;
    emails_opened: number;
    emails_clicked: number;
    replies: number;
    bookings: number;
    leads: number;
    open_rate: number;
    click_rate: number;
    reply_rate: number;
    booking_rate: number;
  };
};

export type AivaAnalyticsWorker = {
  workspace_id: string;
  worker_id?: string | null;
  days: number;
  messages: number;
  escalations: number;
  agent_calls: number;
  tokens: number;
  avg_duration_seconds: number;
  estimated_cost_usd: number;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const raw = search.toString();
  return raw ? `?${raw}` : "";
}

export async function fetchAivaAnalyticsOverview(
  days: AnalyticsPeriodDays,
  workspaceId = "default",
): Promise<AivaAnalyticsOverview> {
  return parseJson(
    await ceApi(`/api/aiva/analytics/overview${qs({ days, workspace_id: workspaceId })}`),
    "Failed to load analytics overview",
  );
}

export async function fetchAivaAnalyticsUsage(
  days: AnalyticsPeriodDays,
  workspaceId = "default",
): Promise<AivaAnalyticsUsage> {
  return parseJson(
    await ceApi(`/api/aiva/analytics/usage${qs({ days, workspace_id: workspaceId })}`),
    "Failed to load analytics usage",
  );
}

export async function fetchAivaAnalyticsOutreach(
  days: AnalyticsPeriodDays,
  workspaceId = "default",
): Promise<AivaAnalyticsOutreach> {
  return parseJson(
    await ceApi(`/api/aiva/analytics/outreach${qs({ days, workspace_id: workspaceId })}`),
    "Failed to load outreach analytics",
  );
}

export async function fetchAivaAnalyticsWorker(
  days: AnalyticsPeriodDays,
  workspaceId = "default",
): Promise<AivaAnalyticsWorker> {
  return parseJson(
    await ceApi(`/api/aiva/analytics/worker${qs({ days, workspace_id: workspaceId })}`),
    "Failed to load worker analytics",
  );
}
