import { ceApi } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

export type AgentServer = {
  id: string;
  name: string;
  url: string;
  owner: string;
  workspace_root: string;
  capabilities: string[];
  sandbox_status: string;
  health_status: string;
  last_heartbeat: string | null;
  has_token: boolean;
};

export type ControlSession = {
  id: string;
  server_id: string;
  task_type: string;
  objective: string;
  status: string;
  requires_approval: boolean;
};

export type QueueRun = {
  id: string;
  status: string;
  payload: Record<string, unknown>;
  logs: string[];
};

export type Automation = {
  id: string;
  name: string;
  trigger_type: string;
  playbook_id?: string;
  enabled: boolean;
  last_run_at?: string | null;
};

export type ControlDashboard = {
  servers: AgentServer[];
  active_sessions: ControlSession[];
  queued_runs: QueueRun[];
  failed_runs: QueueRun[];
  automations: Automation[];
  approvals: Array<Record<string, unknown>>;
  recent_artifacts: Array<Record<string, unknown>>;
  activity: Array<Record<string, unknown>>;
};

export async function fetchControlDashboard() {
  return parseJson<ControlDashboard>(await ceApi("/api/control-center/dashboard"), "control center dashboard");
}

export async function registerAgentServer(body: {
  name: string;
  url: string;
  workspace_root: string;
  token?: string;
}) {
  return parseJson<{ server: AgentServer }>(
    await ceApi("/api/control-center/servers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "register server",
  );
}

export async function createScheduledAutomation(body: {
  name: string;
  playbook_id: string;
  schedule_cron: string;
  server_id?: string;
}) {
  return parseJson<{ automation: Automation }>(
    await ceApi("/api/control-center/automations/schedule", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "schedule automation",
  );
}

export async function triggerAutomation(automationId: string) {
  return parseJson<{ run: QueueRun }>(
    await ceApi(`/api/control-center/automations/${encodeURIComponent(automationId)}/trigger`, {
      method: "POST",
    }),
    "trigger automation",
  );
}

export async function createWebhookAutomation(body: { name: string; playbook_id: string; server_id?: string }) {
  return parseJson<{ automation: Automation; webhook_path: string }>(
    await ceApi("/api/control-center/automations/webhook", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "webhook automation",
  );
}
