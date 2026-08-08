import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
}

function qs(params: Record<string, string | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value == null || value === "") continue;
    search.set(key, value);
  }
  const raw = search.toString();
  return raw ? `?${raw}` : "";
}

export type TypedAgentInventoryRow = {
  name: string;
  tool_count: number;
  tools: string[];
  approval_gated_tools: number;
  output_schema: string;
  deps_schema: string;
};

export async function fetchTypedAgents() {
  return parseJson<{ agents: string[]; inventory?: TypedAgentInventoryRow[]; count?: number }>(
    await ceApi("/api/typed-agents"),
    "Failed to load typed agents",
  );
}

export async function fetchTypedAgentSchemas(name: string) {
  return parseJson<{
    agent_name?: string;
    output_schema?: Record<string, unknown>;
    dependencies_schema?: Record<string, unknown>;
    context_schema?: Record<string, unknown>;
    tools?: Array<{
      name: string;
      description?: string;
      approval_action?: string | null;
      input_schema?: Record<string, unknown>;
      output_schema?: Record<string, unknown> | null;
    }>;
  }>(
    await ceApi(`/api/typed-agents/${encodeURIComponent(name)}/schemas`),
    "Failed to load schemas",
  );
}

export async function runTypedAgent(
  name: string,
  body: {
    workspace_id?: string;
    user_id?: string;
    tool_calls?: Array<{ name: string; arguments?: Record<string, unknown> }>;
    raw_output?: Record<string, unknown>;
    auto_approve?: boolean;
  },
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/typed-agents/${encodeURIComponent(name)}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to run typed agent",
  );
}

export type KernelPluginFunction = {
  name: string;
  description?: string;
  invocation?: string;
  risk_level?: string;
  output_type?: string;
  cost_units?: number;
  permissions?: string[];
};

export type KernelPlugin = {
  name: string;
  version: string;
  risk_level: string;
  documentation: string;
  capability_tags: string[];
  auth_requirements: string[];
  functions: KernelPluginFunction[];
};

export type KernelTrace = {
  plugin: string;
  function: string;
  status: string;
  duration_ms: number | null;
  at: string;
  error: string | null;
};

export async function fetchKernelPlugins() {
  return parseJson<{ plugins: Record<string, unknown>[] }>(
    await ceApi("/api/kernel/plugins"),
    "Failed to load kernel plugins",
  );
}

export async function fetchKernelTraces() {
  return parseJson<{ traces: Record<string, unknown>[] }>(
    await ceApi("/api/kernel/traces"),
    "Failed to load kernel traces",
  );
}

export async function fetchInterfaces(agentId: string) {
  return parseJson<{ agent_id: string; interfaces: Record<string, unknown>[] }>(
    await ceApi(`/api/interfaces/agents/${encodeURIComponent(agentId)}`),
    "Failed to load interfaces",
  );
}

export async function bindInterfaces(agentId: string, kinds: string[]) {
  return parseJson<{ agent_id: string; interfaces: Record<string, unknown>[] }>(
    await ceApi("/api/interfaces/bind", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_id: agentId, kinds }),
    }),
    "Failed to bind interfaces",
  );
}

export async function dispatchInterface(body: {
  agent_id: string;
  kind: string;
  message: string;
  workspace_id?: string;
}) {
  return parseJson<Record<string, unknown>>(
    await ceApi("/api/interfaces/dispatch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to dispatch",
  );
}

export async function fetchIntentSchemas(workspaceId = "default") {
  return parseJson<Record<string, unknown>[]>(
    await ceApi(`/api/intent/schemas${qs({ workspace_id: workspaceId })}`),
    "Failed to load intent schemas",
  );
}

export async function extractIntent(body: {
  translated_text: string;
  workspace_id?: string;
}) {
  return parseJson<Record<string, unknown>>(
    await ceApi("/api/intent/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to extract intent",
  );
}

export async function fetchToolAdapters(category?: string) {
  return parseJson<{ categories: Record<string, number>; adapters: Record<string, unknown>[] }>(
    await ceApi(`/api/tools/adapters${qs({ category })}`),
    "Failed to load adapters",
  );
}

export async function runToolAdapter(
  name: string,
  body: { action: string; params?: Record<string, unknown>; dry_run?: boolean; approved?: boolean },
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/tools/adapters/${encodeURIComponent(name)}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to run adapter",
  );
}

export async function fetchPersonasInventory(workspaceId = "default") {
  return parseJson<{ personas: Record<string, unknown>[] }>(
    await ceApi(`/api/personas${qs({ workspace_id: workspaceId })}`),
    "Failed to load personas",
  );
}

export async function fetchPersonaSkillPacks(name: string) {
  return parseJson<{ persona: string; skill_packs: Record<string, unknown> }>(
    await ceApi(`/api/personas/${encodeURIComponent(name)}/skill-packs`),
    "Failed to load skill packs",
  );
}
