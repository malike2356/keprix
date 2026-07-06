import { buildApiHeaders, ceApi, getApiBaseUrl } from "@/lib/ce-api";

export type AdminTool = {
  id: string;
  name: string;
  description: string;
  source: "builtin" | "synthesised" | "community";
  status: "active" | "disabled";
  last_used_at?: string | null;
  times_called: number;
  created_at?: string;
  tool_code?: string;
  skill_yaml?: string;
  usage?: { labels: string[]; values: number[] };
};

export type MemoryDocument = {
  id: string;
  name: string;
  type: string;
  size_bytes: number;
  chunks: number;
  uploaded_at?: string;
  uploaded_by?: string;
  status: "indexed" | "indexing" | "error";
  preview?: string;
};

export type ChannelOverview = {
  id: string;
  name: string;
  status: string;
  bot_username?: string | null;
  message_count?: number;
  endpoint?: string;
  active_keys?: number;
};

export type ApiKeyRow = {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at?: string | null;
  expires_at?: string | null;
  scopes: string[];
  revoked: boolean;
};

export type WorkspaceUser = {
  id: string;
  name: string;
  email: string;
  role: string;
  status: "active" | "invited" | "suspended";
  joined_at?: string | null;
  last_active_at?: string | null;
  source?: "account" | "invite";
  invite_id?: string;
  expires_at?: string | null;
};

export type WorkspaceInviteResult = {
  invite: {
    id: string;
    email: string;
    role: string;
    status: string;
    expires_at?: string;
  };
  invite_url: string;
  email_sent: boolean;
};

export type AdminSettings = {
  instance_name: string;
  instance_url: string;
  timezone: string;
  language: string;
  max_tool_iterations: number;
  context_compression_threshold: number;
  mutation_engine_enabled: boolean;
  mutation_sandbox_timeout: number;
  auto_approve_owner_mutations: boolean;
  postgres_url: string;
  redis_url: string;
  vector_store_engine: string;
  max_memory_documents: number;
  governance_config: {
    license_key: string;
    audit_policy_url: string;
    provider_endpoint: string;
  };
};

export type GeneratedMutation = {
  id: string;
  tool_name: string;
  description: string;
  gap_description?: string;
  status: string;
  task_that_triggered: string;
  tool_code: string;
  skill_yaml: string;
  sandbox_result?: { passed?: boolean; output?: string; exit_code?: number };
  created_at?: string;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(
      (payload as { detail?: string; error?: string }).detail ||
        (payload as { error?: string }).error ||
        fallback,
    );
  }
  return response.json();
}

export async function fetchAdminTools(search?: string, source?: string) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (source && source !== "all") params.set("source", source);
  const suffix = params.toString() ? `?${params}` : "";
  return parseJson<{ items: AdminTool[]; counts: Record<string, number> }>(
    await ceApi(`/api/tools${suffix}`),
    "tools",
  );
}

export async function fetchAdminTool(toolId: string) {
  return parseJson<AdminTool>(await ceApi(`/api/tools/${toolId}`), "tool");
}

export async function disableAdminTool(toolId: string) {
  await parseJson(await ceApi(`/api/tools/${toolId}/disable`, { method: "POST" }), "disable");
}

export async function deleteAdminTool(toolId: string) {
  await parseJson(await ceApi(`/api/tools/${toolId}`, { method: "DELETE" }), "delete");
}

export async function fetchMemoryDocuments(search?: string) {
  const suffix = search ? `?search=${encodeURIComponent(search)}` : "";
  return parseJson<{
    items: MemoryDocument[];
    stats: { total_documents: number; total_chunks: number; last_indexed_at?: string | null };
  }>(await ceApi(`/api/memory/documents${suffix}`), "memory");
}

export async function fetchMemoryDocument(docId: string) {
  return parseJson<MemoryDocument>(await ceApi(`/api/memory/documents/${docId}`), "document");
}

export async function deleteMemoryDocument(docId: string) {
  await parseJson(await ceApi(`/api/memory/documents/${docId}`, { method: "DELETE" }), "delete");
}

export async function uploadMemoryDocument(file: File) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${getApiBaseUrl()}/api/memory/documents`, {
    method: "POST",
    headers: buildApiHeaders(),
    body: form,
    credentials: "include",
  });
  return parseJson<MemoryDocument>(response, "upload");
}

export async function indexMemoryUrl(url: string) {
  return parseJson(
    await ceApi("/api/memory/documents/url", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),
    "index url",
  );
}

export async function fetchChannelsOverview() {
  return parseJson<{ channels: ChannelOverview[] }>(await ceApi("/api/channels/overview"), "channels");
}

export async function saveTelegramChannel(botToken: string) {
  return parseJson(
    await ceApi("/api/channels/telegram", {
      method: "POST",
      body: JSON.stringify({ bot_token: botToken }),
    }),
    "telegram",
  );
}

export async function fetchTelegramChannelConfig() {
  return parseJson<{ webhook_url: string; configured: boolean }>(
    await ceApi("/api/channels/telegram"),
    "telegram config",
  );
}

export async function testTelegramChannel() {
  return parseJson<{ ok: boolean; message: string }>(
    await ceApi("/api/channels/telegram/test", { method: "POST" }),
    "telegram test",
  );
}

export async function saveDiscordChannel(body: {
  bot_token: string;
  application_id?: string;
  guild_id?: string;
}) {
  return parseJson(
    await ceApi("/api/channels/discord", { method: "POST", body: JSON.stringify(body) }),
    "discord",
  );
}

export async function testDiscordChannel() {
  return parseJson<{ ok: boolean; message: string }>(
    await ceApi("/api/channels/discord/test", { method: "POST" }),
    "discord test",
  );
}

export async function fetchApiKeys() {
  return parseJson<{ keys: ApiKeyRow[] }>(await ceApi("/api/api-keys"), "keys");
}

export async function createApiKey(body: { name: string; expiry: string; scopes: string[] }) {
  return parseJson<{ secret: string } & ApiKeyRow>(
    await ceApi("/api/api-keys", { method: "POST", body: JSON.stringify(body) }),
    "create key",
  );
}

export async function revokeApiKey(keyId: string) {
  await parseJson(await ceApi(`/api/api-keys/${keyId}`, { method: "DELETE" }), "revoke");
}

export async function fetchDeveloperIdentity() {
  return parseJson<{
    fingerprint: string;
    created_at: string;
    public_key_pem?: string;
    config_path: string;
  }>(await ceApi("/api/identity/developer"), "identity");
}

export async function fetchWorkspaceUsers() {
  return parseJson<{
    items: WorkspaceUser[];
    stats: { total: number; active: number; pending_invites: number };
  }>(await ceApi("/api/users"), "users");
}

export async function inviteWorkspaceUser(body: { email: string; role: string; message?: string }) {
  return parseJson<WorkspaceInviteResult>(
    await ceApi("/api/users/invite", { method: "POST", body: JSON.stringify(body) }),
    "invite",
  );
}

export async function updateWorkspaceUser(
  userId: string,
  body: { role?: string; status?: "active" | "invited" | "suspended" },
) {
  return parseJson<{ user: WorkspaceUser }>(
    await ceApi(`/api/users/${encodeURIComponent(userId)}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "update user",
  );
}

export async function deleteWorkspaceUser(userId: string) {
  return parseJson<{ ok: boolean }>(
    await ceApi(`/api/users/${encodeURIComponent(userId)}`, { method: "DELETE" }),
    "delete user",
  );
}

export async function resendWorkspaceInvite(inviteId: string) {
  return parseJson<WorkspaceInviteResult>(
    await ceApi(`/api/users/invites/${encodeURIComponent(inviteId)}/resend`, { method: "POST" }),
    "resend invite",
  );
}

export async function revokeWorkspaceInvite(inviteId: string) {
  return parseJson<{ ok: boolean }>(
    await ceApi(`/api/users/invites/${encodeURIComponent(inviteId)}`, { method: "DELETE" }),
    "revoke invite",
  );
}

export async function fetchInvitePreview(token: string) {
  return parseJson<{ invite: { email: string; role: string; message?: string; expires_at?: string } }>(
    await ceApi(`/api/auth/invites/${encodeURIComponent(token)}`),
    "invite preview",
  );
}

export async function acceptWorkspaceInvite(body: { token: string; password: string; username?: string }) {
  const response = await ceApi("/api/auth/invites/accept", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const message =
      payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail?: string }).detail || "Accept failed")
        : "Accept failed";
    throw new Error(message);
  }
  return response.json() as Promise<{
    token: string;
    user: { id: string; username: string; email?: string; role: string };
  }>;
}

export type CustomProvider = {
  id: string;
  name: string;
  base_url: string;
  default_model?: string | null;
  api_key_set?: boolean;
  connected?: boolean;
  is_default?: boolean;
  kind?: "custom";
};

export async function fetchAdminSettings() {
  return parseJson<{
    settings: AdminSettings;
    providers: Record<string, { connected: boolean; default_model?: string | null; is_default?: boolean }>;
    provider_catalog?: Array<{ id: string; label: string }>;
    custom_providers?: CustomProvider[];
    default_provider?: string;
    governance_enabled: boolean;
  }>(await ceApi("/api/settings"), "settings");
}

export async function saveAdminSettings(settings: Partial<AdminSettings>) {
  return parseJson(
    await ceApi("/api/settings", { method: "PUT", body: JSON.stringify(settings) }),
    "save settings",
  );
}

export async function saveProviderSettings(
  providerId: string,
  body: { api_key?: string; default_model?: string },
) {
  return parseJson(
    await ceApi(`/api/settings/providers/${providerId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "provider",
  );
}

export async function testProviderConnection(providerId: string) {
  return parseJson<{ ok: boolean; message: string }>(
    await ceApi(`/api/settings/providers/${providerId}/test`, { method: "POST" }),
    "provider test",
  );
}

export async function deleteProviderSettings(providerId: string) {
  return parseJson(
    await ceApi(`/api/settings/providers/${providerId}`, { method: "DELETE" }),
    "delete provider",
  );
}

export async function setDefaultProvider(providerId: string) {
  return parseJson(
    await ceApi("/api/settings/default-provider", {
      method: "POST",
      body: JSON.stringify({ provider_id: providerId }),
    }),
    "default provider",
  );
}

export async function createCustomProvider(body: {
  name: string;
  base_url: string;
  api_key?: string;
  default_model?: string;
}) {
  return parseJson<{ provider: CustomProvider }>(
    await ceApi("/api/settings/custom-providers", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "create custom provider",
  );
}

export async function updateCustomProvider(
  providerId: string,
  body: {
    name?: string;
    base_url?: string;
    api_key?: string;
    default_model?: string;
  },
) {
  return parseJson<{ provider: CustomProvider }>(
    await ceApi(`/api/settings/custom-providers/${providerId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "update custom provider",
  );
}

export async function deleteCustomProvider(providerId: string) {
  return parseJson(
    await ceApi(`/api/settings/custom-providers/${providerId}`, { method: "DELETE" }),
    "delete custom provider",
  );
}

export async function testCustomProviderConnection(providerId: string) {
  return parseJson<{ ok: boolean; message: string }>(
    await ceApi(`/api/settings/custom-providers/${providerId}/test`, { method: "POST" }),
    "custom provider test",
  );
}

export type WebSearchEnvVar = {
  key: string;
  prompt: string;
  url?: string;
  secret?: boolean;
};

export type WebSearchCatalogItem = {
  id: string;
  label: string;
  badge?: string;
  description?: string;
  env_vars: WebSearchEnvVar[];
};

export type WebSearchProviderState = {
  connected: boolean;
  is_active?: boolean;
};

export async function fetchWebSearchSettings() {
  return parseJson<{
    active_backend?: string | null;
    providers: Record<string, WebSearchProviderState>;
    catalog: WebSearchCatalogItem[];
  }>(await ceApi("/api/settings/web-search"), "web search settings");
}

export async function saveWebSearchSettings(
  providerId: string,
  body: { env_values?: Record<string, string>; set_active?: boolean },
) {
  return parseJson(
    await ceApi(`/api/settings/web-search/${providerId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "web search provider",
  );
}

export async function testWebSearchProvider(providerId: string) {
  return parseJson<{ ok: boolean; message: string }>(
    await ceApi(`/api/settings/web-search/${providerId}/test`, { method: "POST" }),
    "web search test",
  );
}

export async function deleteWebSearchSettings(providerId: string) {
  return parseJson(
    await ceApi(`/api/settings/web-search/${providerId}`, { method: "DELETE" }),
    "delete web search provider",
  );
}

export async function activateWebSearchProvider(providerId: string) {
  return parseJson(
    await ceApi("/api/settings/web-search/activate", {
      method: "POST",
      body: JSON.stringify({ provider_id: providerId }),
    }),
    "activate web search provider",
  );
}

export async function fetchMutations(status?: string) {
  const response = await ceApi("/api/agent/tools/generated");
  const data = await parseJson<{ tools: GeneratedMutation[] }>(response, "mutations");
  const items = data.tools || [];
  if (!status || status === "all") return items;
  return items.filter((item) => item.status === status);
}

export async function fetchMutation(recordId: string) {
  return parseJson<GeneratedMutation>(
    await ceApi(`/api/agent/tools/generated/${recordId}`),
    "mutation",
  );
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
