import { ceApi } from "@/lib/ce-api";

export type TraceEvent = {
  type: string;
  agent: string;
  payload: Record<string, unknown>;
  at: string;
};

export type TraceView = {
  run_id: string;
  current_agent: string;
  accepted_handoffs: string[];
  events: TraceEvent[];
  summary: {
    agent_events: number;
    handoffs: number;
    guardrails: number;
    tools: number;
    outputs: number;
  };
};

export type RealtimeEvent = {
  type: string;
  text: string;
  payload: Record<string, unknown>;
  at: string;
};

export async function fetchAgentAppRuntimeRuns(app: string, limit = 20) {
  const response = await ceApi(
    `/api/agents-runtime/runs?source=agent_app&app=${encodeURIComponent(app)}&limit=${limit}`,
  );
  if (!response.ok) throw new Error("Failed to load agent app runs");
  return response.json();
}

export async function fetchAgents() {
  const response = await ceApi("/api/agents-runtime/agents");
  if (!response.ok) throw new Error("Failed to load agents");
  return response.json();
}

export async function startAgentRun(body: { agent: string; input: string; state?: Record<string, unknown> }) {
  const response = await ceApi("/api/agents-runtime/runs", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Failed to start agent run");
  return response.json();
}

export async function fetchRunTrace(runId: string): Promise<TraceView> {
  const response = await ceApi(`/api/agents-runtime/runs/${runId}/trace`);
  if (!response.ok) throw new Error("Failed to load trace");
  return response.json();
}

export async function handoffRun(
  runId: string,
  body: { target: string; reason: string; handoff_type?: string; accept?: boolean },
) {
  const response = await ceApi(`/api/agents-runtime/runs/${runId}/handoff`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Handoff failed");
  return response.json();
}

export async function createRealtimeSession(agent = "echo_agent") {
  const response = await ceApi(`/api/agents-runtime/realtime/sessions?agent=${encodeURIComponent(agent)}`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to create realtime session");
  return response.json();
}

export async function postRealtimeEvent(
  sessionId: string,
  body: { type: string; text?: string },
): Promise<{ event: RealtimeEvent; session: { transcript: RealtimeEvent[] } }> {
  const response = await ceApi(`/api/agents-runtime/realtime/sessions/${sessionId}/events`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Failed to post realtime event");
  return response.json();
}

export async function fetchRealtimeTranscript(sessionId: string): Promise<{ transcript: RealtimeEvent[] }> {
  const response = await ceApi(`/api/agents-runtime/realtime/sessions/${sessionId}/transcript`);
  if (!response.ok) throw new Error("Failed to load transcript");
  return response.json();
}
