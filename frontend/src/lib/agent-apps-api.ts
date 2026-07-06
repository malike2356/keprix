import { buildApiHeaders, ceApi, getApiBaseUrl, parseApiErrorMessage } from "@/lib/ce-api";

export type AgentAppInput = {
  id: string;
  label: string;
  type: string;
  required?: boolean;
  default?: string | number | boolean;
  placeholder?: string;
  options?: string[];
};

export type AgentAppOutput = {
  id: string;
  type: string;
};

export type AgentAppSummary = {
  name: string;
  version: string;
  display_name?: string;
  description?: string;
  category?: string;
  icon?: string | null;
  runtime?: string;
  entrypoint?: string;
  source?: string;
  installed_at?: string;
};

export type AgentAppDetail = AgentAppSummary & {
  inputs?: AgentAppInput[];
  outputs?: AgentAppOutput[];
  required_env?: string[];
  required_permissions?: string[];
  eval_suite?: string | null;
  schedule?: { suggested?: string; timezone?: string } | null;
};

export type CatalogTemplate = {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  tier?: string;
  icon?: string;
  featured?: boolean;
  installed?: boolean;
  pro_locked?: boolean;
  readme_excerpt?: string;
  source?: string;
  pack_id?: string;
};

export class AgentAppApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "AgentAppApiError";
    this.status = status;
    this.code = code;
  }
}

export type AgentAppReadiness = {
  ready: boolean;
  missing_env: string[];
  missing_permissions: string[];
  vault_links: Array<{ key: string; href: string }>;
  permission_links?: Array<{ permission: string; href: string; message: string }>;
};

export type AgentRunResult = {
  app: string;
  version: string;
  runner: string;
  trace_id: string;
  result: { output?: string; status?: string };
  traces: Array<{ event: string; payload: Record<string, unknown> }>;
};

export type AgentAppValidation = {
  valid: boolean;
  manifest?: AgentAppDetail;
  error?: string;
};

export type AgentAppInstallResult = {
  app: AgentAppSummary;
  redirect: string;
};

export type AgentAppSchedule = {
  cron_job_id?: string;
  cron: string;
  timezone: string;
  inputs?: Record<string, string>;
  enabled: boolean;
  updated_at?: string;
};

export type AgentAppWebhook = {
  configured?: boolean;
  url?: string;
  token_last4?: string;
  created_at?: string;
};

export type AgentAppWebhookRotate = AgentAppWebhook & {
  url: string;
};

export type AgentAppUsage = {
  runs_this_month: number;
  runs_limit: number | null;
  installed_count: number;
  installed_limit: number | null;
  scheduled_count?: number;
  scheduled_limit?: number | null;
  plan: string;
  near_run_limit?: boolean;
  features?: {
    marketplace?: boolean;
    pro_templates?: boolean;
    scheduled?: boolean;
    webhooks?: boolean;
    publish?: boolean;
  };
};

function parseEntitlementError(payload: unknown, fallback: string) {
  if (!payload || typeof payload !== "object") {
    return { message: fallback, code: undefined as string | undefined };
  }
  const record = payload as Record<string, unknown>;
  const detail = record.detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const block = detail as Record<string, unknown>;
    const message =
      typeof block.message === "string"
        ? block.message
        : typeof block.detail === "string"
          ? block.detail
          : fallback;
    const code = typeof block.detail === "string" ? block.detail : undefined;
    return { message, code };
  }
  if (typeof detail === "string") {
    return { message: detail, code: detail };
  }
  return { message: parseApiErrorMessage(payload, fallback), code: undefined };
}

async function agentAppsForm(path: string, formData: FormData, method = "POST"): Promise<Response> {
  const base = getApiBaseUrl();
  const url = path.startsWith("http") ? path : `${base}${path}`;
  return fetch(url, {
    method,
    headers: buildApiHeaders(),
    body: formData,
    credentials: "include",
  });
}

function parseSemver(version: string): number[] {
  return version
    .replace(/^v/i, "")
    .split(".")
    .map((part) => {
      const digits = part.match(/^\d+/)?.[0];
      return digits ? Number(digits) : 0;
    });
}

export function isNewerVersion(candidate: string, installed: string): boolean {
  const a = parseSemver(candidate);
  const b = parseSemver(installed);
  const length = Math.max(a.length, b.length);
  for (let i = 0; i < length; i += 1) {
    const left = a[i] ?? 0;
    const right = b[i] ?? 0;
    if (left > right) return true;
    if (left < right) return false;
  }
  return false;
}

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const { message, code } = parseEntitlementError(payload, fallback);
    if (response.status === 402) {
      throw new AgentAppApiError(message, response.status, code);
    }
    throw new Error(parseApiErrorMessage(payload, message));
  }
  return response.json();
}

export async function fetchAgentAppUsage() {
  const data = await parseJson<AgentAppUsage>(await ceApi("/api/agent-apps/usage"), "agent app usage");
  return { usage: data };
}

export async function fetchAgentApps() {
  return parseJson<{ apps: AgentAppSummary[] }>(await ceApi("/api/agent-apps"), "agent apps");
}

/** @alias fetchAgentApps */
export async function listAgentApps() {
  const data = await fetchAgentApps();
  return data.apps;
}

export async function fetchAgentApp(name: string) {
  return parseJson<{ app: AgentAppDetail }>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(name)}`),
    "agent app detail",
  );
}

/** @alias fetchAgentApp */
export async function getAgentApp(name: string) {
  const data = await fetchAgentApp(name);
  return data.app;
}

export async function fetchCatalogTemplates(category?: string, q?: string) {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (q) params.set("q", q);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return parseJson<{ templates: CatalogTemplate[] }>(
    await ceApi(`/api/agent-apps/catalog${suffix}`),
    "agent app catalog",
  );
}

export async function installCatalogTemplate(templateId: string) {
  const response = await ceApi(`/api/agent-apps/catalog/${encodeURIComponent(templateId)}/install`, {
    method: "POST",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const { message, code } = parseEntitlementError(payload, "install catalog template");
    throw new AgentAppApiError(message, response.status, code);
  }
  return response.json() as Promise<{ app: AgentAppSummary; redirect: string }>;
}

export async function fetchAgentAppReadiness(name: string) {
  return parseJson<AgentAppReadiness>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(name)}/readiness`),
    "agent app readiness",
  );
}

export async function runAgentApp(
  appName: string,
  payload: { input?: string; inputs?: Record<string, string> },
) {
  return parseJson<AgentRunResult>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(appName)}/run`, {
      method: "POST",
      body: JSON.stringify({ input: payload.input ?? "", inputs: payload.inputs ?? {}, runner: "web" }),
    }),
    "run agent app",
  );
}

export type AgentAppRunSummary = {
  trace_id: string;
  app_name: string;
  status: string;
  runner: string;
  input_preview: string;
  error: string | null;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
};

export type AgentAppRunDetail = AgentAppRunSummary & {
  input: Record<string, unknown>;
  output: Record<string, unknown>;
};

export type AgentAppLifecycleEvent = {
  event: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type AgentAppEvalResult = {
  app: string;
  suite: string;
  passed: number;
  total: number;
  success: boolean;
  cases: Array<{ name: string; passed: boolean; output: string }>;
};

export type AgentAppEvalLast = {
  app: string;
  last: {
    app_name: string;
    ran_at: string;
    result: AgentAppEvalResult;
  } | null;
};

export async function fetchAgentAppRuns(appName: string, limit = 20) {
  return parseJson<{ app: string; runs: AgentAppRunSummary[] }>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(appName)}/runs?limit=${limit}`),
    "agent app runs",
  );
}

export async function fetchAgentAppRun(traceId: string) {
  return parseJson<{ run: AgentAppRunDetail; events: AgentAppLifecycleEvent[] }>(
    await ceApi(`/api/agent-apps/runs/${encodeURIComponent(traceId)}`),
    "agent app run detail",
  );
}

export async function runAgentAppEvals(appName: string) {
  return parseJson<{ result: AgentAppEvalResult; last: { ran_at: string } }>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(appName)}/evals/run`, { method: "POST" }),
    "run agent app evals",
  );
}

export async function fetchAgentAppEvalLast(appName: string) {
  return parseJson<AgentAppEvalLast>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(appName)}/evals/last`),
    "agent app eval last",
  );
}

export async function fetchAgentTraces(appName: string, traceId?: string) {
  const suffix = traceId ? `?trace_id=${encodeURIComponent(traceId)}` : "";
  return parseJson<{ traces: Array<Record<string, unknown>> }>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(appName)}/traces${suffix}`),
    "agent traces",
  );
}

export async function uninstallAgentApp(appName: string) {
  return parseJson<{ ok: boolean }>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(appName)}`, { method: "DELETE" }),
    "uninstall agent app",
  );
}

export async function validateAgentAppUpload(file: File) {
  const form = new FormData();
  form.append("file", file);
  const response = await agentAppsForm("/api/agent-apps/validate/upload", form);
  return parseJson<AgentAppValidation>(response, "validate agent app bundle");
}

export async function installAgentAppUpload(file: File) {
  const form = new FormData();
  form.append("file", file);
  const response = await agentAppsForm("/api/agent-apps/install/upload", form);
  return parseJson<AgentAppInstallResult>(response, "install agent app bundle");
}

export async function installAgentAppFromPath(path: string) {
  return parseJson<AgentAppInstallResult>(
    await ceApi("/api/agent-apps/install", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),
    "install agent app from path",
  );
}

export async function upgradeAgentAppUpload(appName: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  const response = await agentAppsForm(
    `/api/agent-apps/${encodeURIComponent(appName)}/upgrade`,
    form,
  );
  return parseJson<AgentAppInstallResult>(response, "upgrade agent app");
}

export async function downloadAgentAppExport(appName: string) {
  const response = await ceApi(`/api/agent-apps/${encodeURIComponent(appName)}/export`);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Export failed"));
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${appName}.zip`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export async function fetchAgentAppSchedule(appName: string) {
  return parseJson<{ schedule: AgentAppSchedule | null }>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(appName)}/schedule`),
    "agent app schedule",
  );
}

export async function saveAgentAppSchedule(
  appName: string,
  payload: { cron: string; timezone: string; inputs?: Record<string, string>; enabled: boolean },
) {
  return parseJson<{ schedule: AgentAppSchedule }>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(appName)}/schedule`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
    "save agent app schedule",
  );
}

export async function deleteAgentAppSchedule(appName: string) {
  return parseJson<{ ok: boolean }>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(appName)}/schedule`, { method: "DELETE" }),
    "delete agent app schedule",
  );
}

export async function fetchAgentAppWebhook(appName: string) {
  return parseJson<{ webhook: AgentAppWebhook | null }>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(appName)}/webhook`),
    "agent app webhook",
  );
}

export async function rotateAgentAppWebhook(appName: string) {
  return parseJson<{ webhook: AgentAppWebhookRotate }>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(appName)}/webhook/rotate`, {
      method: "POST",
    }),
    "rotate agent app webhook",
  );
}

export async function deleteAgentAppWebhook(appName: string) {
  return parseJson<{ ok: boolean }>(
    await ceApi(`/api/agent-apps/${encodeURIComponent(appName)}/webhook`, { method: "DELETE" }),
    "delete agent app webhook",
  );
}
