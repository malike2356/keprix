import { ceApi } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

export type AgentRole = {
  name: string;
  goal: string;
  backstory?: string;
  tools?: string[];
  connects_to?: string[];
};

export type McpTool = {
  server: string;
  name: string;
  description: string;
  risk: string;
  requires_approval: boolean;
};

export type StudioConnection = {
  from: string;
  to: string;
};

export type StudioPlaybook = {
  name: string;
  workspace_id: string;
  roles: Record<string, Omit<AgentRole, "name">>;
  connections: StudioConnection[];
  group_chat: {
    policy: string;
    supervisor: string;
    participants: string[];
  };
  mcp_servers: Array<{ name: string; trusted: boolean; bound_tools: string[] }>;
};

export async function fetchAgentRoles() {
  return parseJson<{ roles: AgentRole[] }>(await ceApi("/api/multiagent/roles"), "agent roles");
}

export async function fetchMcpTools(server?: string) {
  const query = server ? `?server=${encodeURIComponent(server)}` : "";
  return parseJson<{ tools: McpTool[] }>(await ceApi(`/api/multiagent/workbench/tools${query}`), "mcp tools");
}

export async function savePlaybook(playbook: StudioPlaybook) {
  return parseJson<{ name: string; path: string; yaml: string }>(
    await ceApi("/api/multiagent/playbooks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(playbook),
    }),
    "save playbook",
  );
}

export async function dryRunPlaybook(playbookName: string, input: string) {
  return parseJson<{ run_id: string; dry_run: boolean; messages: unknown[]; events: unknown[] }>(
    await ceApi("/api/multiagent/playbooks/dry-run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ playbook_name: playbookName, input }),
    }),
    "dry run playbook",
  );
}

export async function callAgentTool(agentId: string, input: string, caller = "coordinator") {
  return parseJson<{ agent_id: string; output: string }>(
    await ceApi(`/api/multiagent/agent-tools/${encodeURIComponent(agentId)}/call`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input, caller }),
    }),
    "agent tool call",
  );
}

export async function bindMcpTools(agentId: string, server: string, tools: string[]) {
  return parseJson<{ agent_id: string; bound_tools: string[] }>(
    await ceApi("/api/multiagent/workbench/bind", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_id: agentId, server, tools }),
    }),
    "bind mcp tools",
  );
}

export async function registerMcpServer(name: string, trusted = true) {
  return parseJson<{ server: string; trusted: boolean }>(
    await ceApi(`/api/multiagent/workbench/servers?name=${encodeURIComponent(name)}&trusted=${trusted}`, {
      method: "POST",
    }),
    "register mcp server",
  );
}
