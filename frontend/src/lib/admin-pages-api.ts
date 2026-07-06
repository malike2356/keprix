import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";
import type { AdminSettings } from "@/lib/admin-workspace-api";

export type AdminUser = {
  id: string;
  username: string;
  email: string | null;
  role: string;
  created_at?: string;
  is_active?: boolean;
  is_approved?: boolean;
};

export type AdminModelRow = {
  id: string;
  provider: string;
  model_id: string;
  type: "chat" | "embed";
  enabled: boolean;
  priority?: number;
  input_cost_per_m?: number | null;
  output_cost_per_m?: number | null;
};

export type AdminChannelRow = {
  id: string;
  type: string;
  name: string;
  status: string;
  last_event_at?: string | null;
};

export type AdminBudgetStatus = {
  spent_usd: number;
  monthly_budget_usd: number | null;
  alert_threshold_percent: number;
  percent_used?: number;
  status?: string;
};

export type AdminUsageByModel = {
  model_id: string;
  total_cost_usd: number;
  token_count: number;
};

export type AdminUsageDaily = {
  date: string;
  cost_usd: number;
};

export type MutationCodePayload = {
  id: string;
  source_code: string;
  code?: string;
  name?: string;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
}

export async function fetchAdminUsers(): Promise<AdminUser[]> {
  const data = await parseJson<{ users: AdminUser[] } | AdminUser[]>(
    await ceApi("/api/admin/users"),
    "Failed to load users",
  );
  const rows = Array.isArray(data) ? data : data.users || [];
  return rows.map((row) => ({
    ...row,
    email: row.email ?? null,
    created_at: row.created_at || new Date().toISOString(),
  }));
}

export async function createAdminUser(body: {
  username: string;
  password: string;
  email?: string;
  role: string;
}): Promise<void> {
  await parseJson(
    await ceApi("/api/admin/users", {
      method: "POST",
      body: JSON.stringify({
        username: body.username,
        password: body.password,
        email: body.email,
        role: body.role,
        is_approved: true,
      }),
    }),
    "Failed to create user",
  );
}

export async function deleteAdminUser(id: string): Promise<void> {
  await parseJson(await ceApi(`/api/admin/users/${id}`, { method: "DELETE" }), "Failed to delete user");
}

export async function fetchAdminModels(): Promise<AdminModelRow[]> {
  const data = await parseJson<{ items: AdminModelRow[] }>(
    await ceApi("/api/admin/models"),
    "Failed to load models",
  );
  return (data.items || []).map((row, index) => ({
    ...row,
    priority: row.priority ?? index + 1,
    enabled: row.enabled ?? true,
  }));
}

export async function patchAdminModel(id: string, body: { enabled?: boolean }): Promise<void> {
  await parseJson(
    await ceApi(`/api/admin/models/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
    "Failed to update model",
  );
}

export async function createAdminModel(body: {
  provider: string;
  model_id: string;
  type: string;
  api_key?: string;
  input_cost_per_m?: number;
  output_cost_per_m?: number;
  enabled?: boolean;
}): Promise<void> {
  await parseJson(
    await ceApi("/api/admin/models", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to create model",
  );
}

export async function deleteAdminModel(id: string): Promise<void> {
  await parseJson(await ceApi(`/api/admin/models/${id}`, { method: "DELETE" }), "Failed to delete model");
}

export async function fetchAdminChannels(): Promise<AdminChannelRow[]> {
  const data = await parseJson<AdminChannelRow[] | { channels: AdminChannelRow[] }>(
    await ceApi("/api/admin/channels"),
    "Failed to load channels",
  );
  if (Array.isArray(data)) return data;
  return data.channels || [];
}

export async function createAdminChannel(body: Record<string, unknown>): Promise<void> {
  await parseJson(
    await ceApi("/api/admin/channels", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to create channel",
  );
}

export async function deleteAdminChannel(id: string): Promise<void> {
  await parseJson(await ceApi(`/api/admin/channels/${id}`, { method: "DELETE" }), "Failed to delete channel");
}

export async function fetchAdminBudgetStatus(): Promise<AdminBudgetStatus> {
  return parseJson(await ceApi("/api/admin/budget/status"), "Failed to load budget");
}

export async function updateAdminBudget(body: {
  monthly_budget_usd: number | null;
  alert_threshold_percent: number;
}): Promise<void> {
  await parseJson(
    await ceApi("/api/admin/budget", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "Failed to save budget",
  );
}

export async function fetchAdminUsageByModel(days = 30): Promise<AdminUsageByModel[]> {
  const rows = await parseJson<
    Array<{ model?: string; model_id?: string; cost_usd?: number; total_cost_usd?: number; request_count?: number }>
  >(await ceApi(`/api/admin/usage/by-model?days=${days}`), "Failed to load usage by model");
  return rows.map((row) => ({
    model_id: row.model_id || row.model || "unknown",
    total_cost_usd: row.total_cost_usd ?? row.cost_usd ?? 0,
    token_count: row.request_count ?? 0,
  }));
}

export async function fetchAdminUsageDaily(days = 30): Promise<AdminUsageDaily[]> {
  const rows = await parseJson<Array<{ date: string; cost_usd: number }>>(
    await ceApi(`/api/admin/usage/daily?days=${days}`),
    "Failed to load daily usage",
  );
  return rows;
}

export async function fetchAdminSettingsPayload(): Promise<{
  settings: AdminSettings;
  default_provider?: string;
}> {
  const response = await ceApi("/api/admin/settings");
  if (!response.ok) {
    const fallback = await ceApi("/api/settings");
    return parseJson(fallback, "Failed to load settings");
  }
  return parseJson(response, "Failed to load settings");
}

export async function saveAdminSettingsPayload(settings: AdminSettings): Promise<void> {
  const response = await ceApi("/api/admin/settings", {
    method: "PUT",
    body: JSON.stringify(settings),
  });
  if (!response.ok) {
    const fallback = await ceApi("/api/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    });
    await parseJson(fallback, "Failed to save settings");
    return;
  }
  await parseJson(response, "Failed to save settings");
}

export type GeneratedToolMutation = {
  id: string;
  tool_name: string;
  status: string;
  requested_by: string;
  requested_at: string;
  task_that_triggered?: string;
  workspace_id?: string;
};

export async function fetchGeneratedToolMutations(limit = 50): Promise<GeneratedToolMutation[]> {
  const data = await parseJson<{ items: GeneratedToolMutation[] }>(
    await ceApi(`/api/mutations?limit=${limit}&sort=created_at:desc`),
    "Failed to load mutations",
  );
  return data.items || [];
}

export async function fetchMutationCode(id: string): Promise<MutationCodePayload> {
  const response = await ceApi(`/api/mutations/${id}/code`);
  if (response.ok) {
    const data = await response.json();
    return {
      id: data.id || id,
      source_code: data.source_code || data.code || "",
      name: data.name,
    };
  }
  const fallback = await ceApi(`/api/mutation/tools/${id}/source`);
  const data = await parseJson<{ source_code: string; name: string }>(fallback, "Failed to load mutation code");
  return { id, source_code: data.source_code, name: data.name };
}
