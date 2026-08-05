import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type A2AAgent = {
  id: string;
  name: string;
  description: string;
  capabilities: string[];
  input_modes?: string[];
  output_modes?: string[];
  endpoint?: string;
  tags?: string[];
};

export type A2ATask = {
  id: string;
  description: string;
  status: "pending" | "running" | "streaming" | "completed" | "failed" | "cancelled" | string;
  agent_id?: string | null;
  created_at?: string;
  updated_at?: string;
  artifact_count?: number;
  error?: string | null;
};

export type A2ATaskArtifact = {
  type: string;
  content: unknown;
  step?: string | null;
  created_at?: string;
};

export type A2AStatus = {
  enabled: boolean;
  agent_count: number;
  task_count: number;
  tasks_by_status: Record<string, number>;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return payload as T;
}

export async function fetchA2AStatus(): Promise<A2AStatus> {
  return parseJson(await ceApi("/api/a2a/status"), "Failed to load A2A status");
}

export async function fetchA2AAgents(): Promise<A2AAgent[]> {
  const data = await parseJson<{ agents: A2AAgent[] }>(
    await ceApi("/api/a2a/agents"),
    "Failed to load A2A agents",
  );
  return data.agents || [];
}

export async function registerA2AAgent(body: {
  id: string;
  name: string;
  description?: string;
  capabilities?: string[];
  tags?: string[];
  endpoint?: string;
}): Promise<A2AAgent> {
  const data = await parseJson<{ agent: A2AAgent }>(
    await ceApi("/api/a2a/agents", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to register agent",
  );
  return data.agent;
}

export async function unregisterA2AAgent(agentId: string): Promise<void> {
  await parseJson(
    await ceApi(`/api/a2a/agents/${encodeURIComponent(agentId)}`, { method: "DELETE" }),
    "Failed to remove agent",
  );
}

export async function fetchA2ATasks(): Promise<A2ATask[]> {
  const data = await parseJson<{ tasks: A2ATask[] }>(
    await ceApi("/api/a2a/tasks"),
    "Failed to load A2A tasks",
  );
  return data.tasks || [];
}

export async function createA2ATask(body: {
  description: string;
  agent_id?: string;
  metadata?: Record<string, unknown>;
}): Promise<A2ATask | null> {
  const data = await parseJson<{ task: A2ATask | null }>(
    await ceApi("/api/a2a/tasks", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to create task",
  );
  return data.task;
}

export async function fetchA2ATask(taskId: string): Promise<{ task: A2ATask; artifacts: A2ATaskArtifact[] }> {
  return parseJson(
    await ceApi(`/api/a2a/tasks/${encodeURIComponent(taskId)}`),
    "Failed to load task",
  );
}

export async function cancelA2ATask(taskId: string): Promise<A2ATask | null> {
  const data = await parseJson<{ task: A2ATask | null }>(
    await ceApi(`/api/a2a/tasks/${encodeURIComponent(taskId)}/cancel`, { method: "POST" }),
    "Failed to cancel task",
  );
  return data.task;
}
