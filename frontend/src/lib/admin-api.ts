import { buildApiHeaders, ceApi, getApiBaseUrl, mcpApi, parseApiErrorMessage } from "@/lib/ce-api";

export type CronJob = {
  id: string;
  name: string;
  schedule: string;
  prompt: string;
  enabled?: boolean;
  deliver?: string;
  next_run_at?: string | null;
  last_run_at?: string | null;
  source?: string | null;
  source_href?: string | null;
};

export type CronRun = {
  id: string;
  started_at?: number;
  ended_at?: number | null;
  is_active?: boolean;
};

export type McpServer = {
  name: string;
  transport: "stdio" | "http" | "sse" | "unknown";
  url?: string | null;
  command?: string | null;
  args?: string[];
  env?: Record<string, string>;
  auth?: string | null;
  enabled: boolean;
  tools?: string[] | null;
  auto_spawned?: boolean;
  oauth_connected?: boolean;
  connection_status?:
    | "connected"
    | "needs_oauth"
    | "needs_credentials"
    | "disabled"
    | "error";
  connection_error?: string | null;
};

export type McpServerInput = {
  name: string;
  url?: string;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  auth?: string;
  transport?: "sse";
};

export type BackupMeta = {
  id: string;
  created_at: string;
  size_bytes?: number;
  filename?: string;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
}

export async function fetchCronJobs(): Promise<CronJob[]> {
  const data = await parseJson<CronJob[] | { jobs?: CronJob[] }>(
    await ceApi("/api/cron/jobs"),
    "Failed to load cron jobs",
  );
  return Array.isArray(data) ? data : data.jobs || [];
}

export async function createCronJob(body: {
  name: string;
  schedule: string;
  prompt: string;
  deliver?: string;
}): Promise<CronJob> {
  return parseJson(
    await ceApi("/api/cron/jobs", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to create job",
  );
}

export async function triggerCronJob(jobId: string): Promise<void> {
  await parseJson(
    await ceApi(`/api/cron/jobs/${jobId}/trigger`, { method: "POST" }),
    "Failed to trigger job",
  );
}

export async function pauseCronJob(jobId: string): Promise<void> {
  await parseJson(
    await ceApi(`/api/cron/jobs/${jobId}/pause`, { method: "POST" }),
    "Failed to pause job",
  );
}

export async function resumeCronJob(jobId: string): Promise<void> {
  await parseJson(
    await ceApi(`/api/cron/jobs/${jobId}/resume`, { method: "POST" }),
    "Failed to resume job",
  );
}

export async function deleteCronJob(jobId: string): Promise<void> {
  await parseJson(
    await ceApi(`/api/cron/jobs/${jobId}`, { method: "DELETE" }),
    "Failed to delete job",
  );
}

export async function fetchCronRuns(jobId: string): Promise<CronRun[]> {
  const data = await parseJson<{ runs: CronRun[] }>(
    await ceApi(`/api/cron/jobs/${jobId}/runs`),
    "Failed to load run history",
  );
  return data.runs;
}

export async function fetchMcpServers(): Promise<McpServer[]> {
  const data = await parseJson<{ servers: McpServer[] }>(
    await mcpApi("/api/mcp/servers"),
    "Failed to load MCP servers",
  );
  return data.servers;
}

export async function addMcpServer(body: McpServerInput): Promise<McpServer> {
  return parseJson(
    await mcpApi("/api/mcp/servers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to add server",
  );
}

export async function updateMcpServer(name: string, body: McpServerInput): Promise<McpServer> {
  return parseJson(
    await mcpApi(`/api/mcp/servers/${encodeURIComponent(name)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to update server",
  );
}

export async function deleteMcpServer(name: string): Promise<void> {
  await parseJson(
    await mcpApi(`/api/mcp/servers/${encodeURIComponent(name)}`, { method: "DELETE" }),
    "Failed to delete server",
  );
}

export async function setMcpServerEnabled(name: string, enabled: boolean): Promise<void> {
  await parseJson(
    await mcpApi(`/api/mcp/servers/${encodeURIComponent(name)}/enabled`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    }),
    "Failed to update server",
  );
}

export async function testMcpServer(
  name: string,
): Promise<{ ok: boolean; tools: Array<string | { name: string; description?: string }>; error?: string }> {
  return parseJson(
    await mcpApi(`/api/mcp/servers/${encodeURIComponent(name)}/test`, { method: "POST" }),
    "Connection test failed",
  );
}

export async function startMcpOAuth(
  name: string,
): Promise<{ authorization_url?: string; ok?: boolean; message?: string; oauth_connected?: boolean }> {
  return parseJson(
    await mcpApi(`/api/mcp/servers/${encodeURIComponent(name)}/oauth/start`, { method: "POST" }),
    "Failed to start OAuth",
  );
}

export type McpVaultSecretKey = { id: string; label: string };

export async function fetchMcpVaultSecretKeys(): Promise<McpVaultSecretKey[]> {
  const data = await parseJson<{ keys: McpVaultSecretKey[] }>(
    await mcpApi("/api/mcp/vault/secret-keys"),
    "Failed to load Vault keys",
  );
  return data.keys;
}

export type McpCatalogEntry = {
  key: string;
  label: string;
  description: string;
  transport: "stdio" | "http";
  command?: string;
  args?: string[];
  required_env: string[];
  capability_tags: string[];
  homepage?: string;
  auth_type?: "oauth" | null;
  auto_spawnable: boolean;
};

export type OptionalMcpCatalogEntry = {
  name: string;
  description: string;
  source: string;
  transport: "stdio" | "http";
  auth_type: string;
  required_env: Array<{ name: string; prompt: string; required: boolean }>;
  needs_install: boolean;
  installed: boolean;
  enabled: boolean;
  docs_url?: string | null;
  category?: string | null;
  default_tools?: string[] | null;
};

export async function fetchMcpCatalog(): Promise<McpCatalogEntry[]> {
  const data = await parseJson<{ catalog: McpCatalogEntry[] }>(
    await mcpApi("/api/mcp/catalog"),
    "Failed to load MCP catalog",
  );
  return data.catalog;
}

export async function fetchOptionalMcpCatalogEntries(): Promise<OptionalMcpCatalogEntry[]> {
  const data = await parseJson<{ entries: OptionalMcpCatalogEntry[] }>(
    await mcpApi("/api/mcp/catalog"),
    "Failed to load optional MCP catalog",
  );
  return data.entries ?? [];
}

export async function installOptionalMcpEntry(
  name: string,
  opts?: { env?: Record<string, string>; enable?: boolean },
): Promise<{ ok: boolean; name: string; background?: boolean }> {
  return parseJson(
    await mcpApi("/api/mcp/catalog/install", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, enable: opts?.enable ?? true, env: opts?.env ?? {} }),
    }),
    "Failed to install MCP catalog entry",
  );
}

export async function addMcpFromCatalog(
  key: string,
  opts?: { name?: string; env?: Record<string, string>; vault_env?: Record<string, string> },
): Promise<McpServer> {
  return parseJson(
    await mcpApi(`/api/mcp/catalog/${encodeURIComponent(key)}/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(opts ?? {}),
    }),
    "Failed to add from catalog",
  );
}

export type AutoSpawnStatus = {
  enabled: boolean;
  auto_spawned_servers: string[];
  env_locked: boolean;
  source: "env" | "config";
};

export async function fetchAutoSpawnStatus(): Promise<AutoSpawnStatus> {
  return parseJson<AutoSpawnStatus>(
    await mcpApi("/api/mcp/auto-spawn/status"),
    "Failed to load auto-spawn status",
  );
}

export async function setAutoMcpSpawnEnabled(enabled: boolean): Promise<AutoSpawnStatus> {
  return parseJson<AutoSpawnStatus>(
    await mcpApi("/api/mcp/auto-spawn/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    }),
    "Failed to update auto-spawn settings",
  );
}

export async function removeAutoSpawnedServer(name: string): Promise<void> {
  await parseJson(
    await mcpApi(`/api/mcp/auto-spawn/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),
    "Failed to remove auto-spawned server",
  );
}

export async function listBackups(): Promise<BackupMeta[]> {
  const data = await parseJson<{ backups: BackupMeta[] }>(
    await ceApi("/api/admin/backup/list"),
    "Failed to list backups",
  );
  return data.backups;
}

export async function createBackup(password?: string): Promise<BackupMeta> {
  return parseJson(
    await ceApi("/api/admin/backup/create", {
      method: "POST",
      body: JSON.stringify({ password: password || null }),
    }),
    "Failed to create backup",
  );
}

export async function deleteBackup(backupId: string): Promise<void> {
  await parseJson(
    await ceApi(`/api/admin/backup/${backupId}`, { method: "DELETE" }),
    "Failed to delete backup",
  );
}

export function backupDownloadUrl(backupId: string): string {
  return `${getApiBaseUrl()}/api/admin/backup/${backupId}/download`;
}

export async function restoreBackup(file: File, password?: string): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  const url = password
    ? `${getApiBaseUrl()}/api/admin/backup/restore?password=${encodeURIComponent(password)}`
    : `${getApiBaseUrl()}/api/admin/backup/restore`;
  const response = await fetch(url, {
    method: "POST",
    headers: buildApiHeaders(),
    body: form,
    credentials: "include",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { detail?: string }).detail || "Restore failed");
  }
}
