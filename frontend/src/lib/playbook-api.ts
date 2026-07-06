import { ceApi } from "@/lib/ce-api";

export type HardwareScan = {
  platform: string;
  architecture: string;
  cpu_cores: number;
  total_ram_gb: number;
  available_ram_gb: number;
  free_disk_gb: number;
  gpu_vendor: string;
  gpu_vram_gb: number;
  has_gpu: boolean;
  gpus: Array<{ index: number; name: string; vram_gb: number }>;
};

export type PlaybookModel = {
  id: string;
  name: string;
  family: string;
  size_b: number;
  quant: string;
  vram_gb: number;
  fit_score: number;
  benchmark_score: number;
  vision_capable: boolean;
};

export async function scanHardware(): Promise<HardwareScan> {
  const response = await ceApi("/api/playbook/scan");
  if (!response.ok) {
    throw new Error("Hardware scan failed");
  }
  return response.json();
}

export async function listPlaybookModels(): Promise<{
  hardware: HardwareScan;
  models: PlaybookModel[];
}> {
  const response = await ceApi("/api/playbook/models");
  if (!response.ok) {
    throw new Error("Failed to load models");
  }
  return response.json();
}

export async function startModelDownload(modelId: string): Promise<{ job_id: string }> {
  const response = await ceApi(`/api/playbook/models/${modelId}/download`, { method: "POST" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { detail?: string }).detail || "Download failed");
  }
  return response.json();
}

export async function serveModel(modelId: string): Promise<{ port: number; backend: string }> {
  const response = await ceApi(`/api/playbook/models/${modelId}/serve`, { method: "POST" });
  if (!response.ok) {
    throw new Error("Failed to register model for serving");
  }
  return response.json();
}

export async function listServing(): Promise<
  Array<{ model_id: string; backend: string; port: number }>
> {
  const response = await ceApi("/api/playbook/serving");
  if (!response.ok) {
    return [];
  }
  const data = (await response.json()) as { serving: Array<{ model_id: string; backend: string; port: number }> };
  return data.serving;
}

// ---- Durable playbook runtime (Prompt 194) ----

export type PlaybookRunStatus =
  | "pending"
  | "running"
  | "paused"
  | "interrupted"
  | "waiting_for_approval"
  | "completed"
  | "failed"
  | "cancelled";

export type PlaybookRun = {
  run_id: string;
  graph_id: string;
  workspace_id: string;
  status: PlaybookRunStatus;
  state: Record<string, unknown>;
  current_node?: string | null;
  error?: string | null;
  interrupt_reason?: string | null;
  approval_request?: Record<string, unknown> | null;
  artifacts?: Array<Record<string, unknown>>;
};

export type PlaybookEvent = {
  event_id: string;
  event_type: string;
  run_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
};

export type PlaybookGraphTemplate = {
  graph_id: string;
  title: string;
  description: string;
  entry?: string | null;
  steps: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
};

async function parsePlaybookJson<T>(response: Response, label: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { detail?: string }).detail || `Failed to load ${label}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchPlaybookGraphs(): Promise<PlaybookGraphTemplate[]> {
  const data = await parsePlaybookJson<{ graphs: PlaybookGraphTemplate[] }>(
    await ceApi("/api/playbook-runs/graphs"),
    "playbook templates",
  );
  return data.graphs || [];
}

export async function fetchPlaybookRuns(workspaceId = "default"): Promise<{
  runs: PlaybookRun[];
  count: number;
  interrupted_count: number;
}> {
  const query = new URLSearchParams({ workspace_id: workspaceId, limit: "50" });
  return parsePlaybookJson(
    await ceApi(`/api/playbook-runs?${query.toString()}`),
    "playbook runs",
  );
}

export function interruptedPlaybookCount(runs: PlaybookRun[]): number {
  return runs.filter((run) =>
    run.status === "interrupted" || run.status === "waiting_for_approval",
  ).length;
}

export async function startPlaybookRun(body: {
  graph_id: string;
  workspace_id?: string;
  initial_state?: Record<string, unknown>;
  steps?: Array<Record<string, unknown>>;
  edges?: Array<Record<string, unknown>>;
  entry?: string;
}): Promise<PlaybookRun> {
  return parsePlaybookJson(
    await ceApi("/api/playbook-runs/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "playbook run",
  );
}

export async function fetchPlaybookRun(runId: string): Promise<PlaybookRun> {
  return parsePlaybookJson(await ceApi(`/api/playbook-runs/${runId}`), "playbook run");
}

export async function fetchPlaybookRunEvents(runId: string): Promise<{ events: PlaybookEvent[] }> {
  return parsePlaybookJson(await ceApi(`/api/playbook-runs/${runId}/events`), "playbook events");
}

export async function resumePlaybookRun(
  runId: string,
  patch?: Record<string, unknown>,
  approvedBy?: string,
): Promise<PlaybookRun> {
  return parsePlaybookJson(
    await ceApi(`/api/playbook-runs/${runId}/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state_patch: patch || {}, approved_by: approvedBy || null }),
    }),
    "playbook resume",
  );
}

export async function pausePlaybookRun(runId: string): Promise<PlaybookRun> {
  return parsePlaybookJson(
    await ceApi(`/api/playbook-runs/${runId}/pause`, { method: "POST" }),
    "playbook pause",
  );
}

export async function cancelPlaybookRun(runId: string): Promise<PlaybookRun> {
  return parsePlaybookJson(
    await ceApi(`/api/playbook-runs/${runId}/cancel`, { method: "POST" }),
    "playbook cancel",
  );
}

export function approvalResumePatch(run: PlaybookRun): Record<string, unknown> {
  const stepId = run.approval_request?.step_id;
  if (typeof stepId === "string" && stepId.trim()) {
    return { [`${stepId}_approved`]: true };
  }
  return { approved: true };
}

export function formatPlaybookEventLabel(event: PlaybookEvent): string {
  const type = event.event_type.replace("playbook.", "").replace(/\./g, " ");
  const node = event.payload.node;
  if (typeof node === "string" && node) {
    return `${type}: ${node}`;
  }
  return type;
}
