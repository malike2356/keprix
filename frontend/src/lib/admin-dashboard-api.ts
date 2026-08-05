import { ceApi } from "@/lib/ce-api";

export type DashboardStats = {
  conversations: number;
  tools: number;
  mutationsApproved: number;
  memoryDocuments: number;
  llmSpend30d: number;
  llmTokens30d: number;
  llmRequestCount30d: number;
  mutationDivergencePercent: number;
  conversationsToday?: number;
  mutationsPendingReview?: number;
  activeAgents?: number;
};

export type DailySeries = { labels: string[]; values: number[] };
export type DailyPoint = { date: string; count: number };

export type ToolBreakdown = { labels: string[]; values: number[] };
export type ToolBreakdownRow = { tool_name: string; call_count: number; success_rate: number };

export type MutationRow = {
  id: string;
  tool_name: string;
  status: string;
  requested_by: string;
  requested_at: string;
  workspace_id?: string;
};

export type ConversationRow = {
  id: string;
  title: string;
  preview: unknown;
  model?: string;
  message_count?: number;
  created_at?: string;
  updated_at?: string;
  user_id?: string;
};

export type ChannelStatus = {
  id: string;
  name: string;
  type?: string;
  status: "connected" | "degraded" | "error" | "healthy" | "disconnected";
  last_message_at?: string | null;
  last_event_at?: string | null;
  configure_href: string;
};

type AdminStatsPayload = {
  total_conversations: number;
  active_agents: number;
  tools_synthesised: number;
  llm_cost_usd_mtd: number;
  conversations_today: number;
  mutations_pending_review: number;
  active_tools?: number;
  memory_documents?: number;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw new Error(fallback);
  }
  return response.json();
}

async function tryAdminJson<T>(path: string): Promise<T | null> {
  try {
    const response = await ceApi(path);
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

function dailySeriesFromPoints(points: DailyPoint[]): DailySeries {
  return {
    labels: points.map((point) => point.date),
    values: points.map((point) => point.count),
  };
}

function mapAdminMutation(row: {
  id: string;
  name: string;
  status: string;
  created_at: string;
  workspace_id?: string;
}): MutationRow {
  return {
    id: row.id,
    tool_name: row.name,
    status: row.status === "staged" ? "pending" : row.status,
    requested_by: "mutation_engine",
    requested_at: row.created_at,
    workspace_id: row.workspace_id,
  };
}

function mapAdminConversation(row: {
  id: string;
  title: string;
  model?: string;
  message_count?: number;
  created_at?: string;
  user_id?: string;
}): ConversationRow {
  return {
    id: row.id,
    title: row.title,
    preview: "",
    model: row.model,
    message_count: row.message_count,
    created_at: row.created_at,
    updated_at: row.created_at,
    user_id: row.user_id,
  };
}

function mapAdminChannel(row: {
  id: string;
  type?: string;
  name: string;
  status: string;
  last_event_at?: string | null;
}): ChannelStatus {
  const status =
    row.status === "healthy"
      ? "connected"
      : row.status === "disconnected"
        ? "degraded"
        : "error";
  return {
    id: row.id,
    name: row.name,
    type: row.type,
    status,
    last_message_at: row.last_event_at,
    last_event_at: row.last_event_at,
    configure_href: "/admin/channels",
  };
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const admin = await tryAdminJson<AdminStatsPayload>("/api/admin/stats");

  if (admin) {
    const [llm, memory, compounding] = await Promise.all([
      parseJson<{
        llmSpend30d: number;
        llmTokens30d: number;
        llmRequestCount30d: number;
      }>(await ceApi("/api/stats/llm/summary?days=30"), "llm stats").catch(() => ({
        llmSpend30d: admin.llm_cost_usd_mtd,
        llmTokens30d: 0,
        llmRequestCount30d: 0,
      })),
      parseJson<{ count: number }>(await ceApi("/api/stats/memory/count"), "memory stats").catch(
        () => ({ count: admin.memory_documents ?? 0 }),
      ),
      parseJson<{ divergence_score: number }>(
        await ceApi("/api/stats/mutations/compounding"),
        "mutation compounding",
      ).catch(() => ({ divergence_score: 0 })),
    ]);

    return {
      conversations: admin.total_conversations,
      tools: admin.active_tools ?? admin.tools_synthesised,
      mutationsApproved: admin.tools_synthesised,
      memoryDocuments: memory.count,
      llmSpend30d: admin.llm_cost_usd_mtd || llm.llmSpend30d,
      llmTokens30d: llm.llmTokens30d,
      llmRequestCount30d: llm.llmRequestCount30d,
      mutationDivergencePercent: Math.round((compounding.divergence_score || 0) * 100),
      conversationsToday: admin.conversations_today,
      mutationsPendingReview: admin.mutations_pending_review,
      activeAgents: admin.active_agents,
    };
  }

  const [conversations, tools, mutations, memory, llm, compounding] = await Promise.all([
    parseJson<{ count: number }>(await ceApi("/api/stats/conversations/count"), "stats"),
    parseJson<{ count: number }>(await ceApi("/api/stats/tools/count"), "stats"),
    parseJson<{ count: number }>(await ceApi("/api/stats/mutations/approved"), "stats"),
    parseJson<{ count: number }>(await ceApi("/api/stats/memory/count"), "stats"),
    parseJson<{
      llmSpend30d: number;
      llmTokens30d: number;
      llmRequestCount30d: number;
    }>(await ceApi("/api/stats/llm/summary?days=30"), "llm stats").catch(() => ({
      llmSpend30d: 0,
      llmTokens30d: 0,
      llmRequestCount30d: 0,
    })),
    parseJson<{ divergence_score: number }>(
      await ceApi("/api/stats/mutations/compounding"),
      "mutation compounding",
    ).catch(() => ({ divergence_score: 0 })),
  ]);
  return {
    conversations: conversations.count,
    tools: tools.count,
    mutationsApproved: mutations.count,
    memoryDocuments: memory.count,
    llmSpend30d: llm.llmSpend30d,
    llmTokens30d: llm.llmTokens30d,
    llmRequestCount30d: llm.llmRequestCount30d,
    mutationDivergencePercent: Math.round((compounding.divergence_score || 0) * 100),
  };
}

export async function fetchConversationDaily(): Promise<DailySeries> {
  const admin = await tryAdminJson<DailyPoint[]>("/api/admin/conversations/daily?days=30");
  if (admin?.length) return dailySeriesFromPoints(admin);
  return parseJson(await ceApi("/api/stats/conversations/daily"), "daily stats");
}

export async function fetchMutationActiveDaily(): Promise<DailySeries> {
  const admin = await tryAdminJson<DailyPoint[]>("/api/admin/mutations/daily?days=30");
  if (admin?.length) return dailySeriesFromPoints(admin);
  return parseJson(await ceApi("/api/stats/mutations/active-daily"), "mutation daily stats");
}

export async function fetchToolBreakdown(): Promise<ToolBreakdown> {
  return parseJson(await ceApi("/api/stats/tools/breakdown"), "tool breakdown");
}

export async function fetchToolUsageBreakdown(limit = 8): Promise<ToolBreakdownRow[]> {
  const admin = await tryAdminJson<ToolBreakdownRow[]>(`/api/admin/tools/breakdown?limit=${limit}`);
  if (admin) return admin;
  return [];
}

export async function fetchRecentMutations(limit = 5): Promise<MutationRow[]> {
  const admin = await tryAdminJson<
    Array<{ id: string; name: string; status: string; created_at: string; workspace_id?: string }>
  >(`/api/admin/mutations?limit=${limit}&sort=created_at:desc`);
  if (admin) return admin.map(mapAdminMutation);

  const data = await parseJson<{ items: MutationRow[] }>(
    await ceApi(`/api/mutations?limit=${limit}&sort=created_at:desc`),
    "mutations",
  );
  return data.items;
}

export async function fetchRecentConversations(limit = 5): Promise<ConversationRow[]> {
  const admin = await tryAdminJson<
    Array<{
      id: string;
      title: string;
      model?: string;
      message_count?: number;
      created_at?: string;
      user_id?: string;
    }>
  >(`/api/admin/conversations?limit=${limit}&sort=created_at:desc`);
  if (admin) return admin.map(mapAdminConversation);

  const data = await parseJson<{ items: ConversationRow[] }>(
    await ceApi(`/api/conversations?limit=${limit}&sort=created_at:desc`),
    "conversations",
  );
  return data.items;
}

export async function fetchChannelStatus(): Promise<ChannelStatus[]> {
  const admin = await tryAdminJson<
    Array<{ id: string; type?: string; name: string; status: string; last_event_at?: string | null }>
  >("/api/admin/channels/status");
  if (admin) return admin.map(mapAdminChannel);

  const data = await parseJson<{ channels: ChannelStatus[] }>(
    await ceApi("/api/channels/status"),
    "channels",
  );
  return data.channels;
}

export async function fetchPendingMutationCount(): Promise<number> {
  const data = await parseJson<{ staged: number }>(
    await ceApi("/api/mutation/stats"),
    "pending count",
  );
  return data.staged ?? 0;
}
