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

export async function startModelDownload(modelId: string): Promise<{ job_id: string; status?: string }> {
  const response = await ceApi(`/api/playbook/models/${modelId}/download`, { method: "POST" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { detail?: string }).detail || "Download failed");
  }
  return response.json();
}

export async function serveModel(modelId: string): Promise<{ port: number; backend: string; job_id?: string }> {
  const response = await ceApi(`/api/playbook/models/${modelId}/serve`, { method: "POST" });
  if (!response.ok) {
    throw new Error("Failed to register model for serving");
  }
  return response.json();
}

export async function stopModel(modelId: string): Promise<{ stopped: boolean }> {
  const response = await ceApi(`/api/playbook/models/${encodeURIComponent(modelId)}/stop`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error("Failed to stop serving");
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

export async function pingServingHealth(port = 11434): Promise<{
  ok: boolean;
  port: number;
  base_url: string;
  error?: string;
  fix?: string;
  status_code?: number;
}> {
  const response = await ceApi(`/api/playbook/serving/health?port=${port}`);
  if (!response.ok) {
    return {
      ok: false,
      port,
      base_url: `http://127.0.0.1:${port}/v1`,
      error: "Health probe failed",
      fix: "Confirm the API can reach the local Ollama daemon.",
    };
  }
  return response.json();
}

export type DownloadProgressEvent = {
  progress_pct?: number;
  status?: string;
  log?: string[];
};

/** Poll SSE download progress until complete/failed. Returns final percent. */
export async function watchModelDownload(
  modelId: string,
  onProgress: (event: DownloadProgressEvent) => void,
  signal?: AbortSignal,
): Promise<DownloadProgressEvent> {
  const response = await ceApi(`/api/playbook/models/${encodeURIComponent(modelId)}/download/status`);
  if (!response.ok || !response.body) {
    throw new Error("No download progress stream");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let last: DownloadProgressEvent = { progress_pct: 0 };

  while (true) {
    if (signal?.aborted) {
      await reader.cancel();
      throw new DOMException("Aborted", "AbortError");
    }
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";
    for (const chunk of chunks) {
      const line = chunk.split("\n").find((part) => part.startsWith("data: "));
      if (!line) continue;
      try {
        last = JSON.parse(line.slice(6)) as DownloadProgressEvent;
        onProgress(last);
      } catch {
        // ignore malformed SSE frames
      }
    }
  }
  return last;
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

export type PlaybookNodeEventPayload = {
  node?: string;
  input_state?: Record<string, unknown>;
  output_state?: Record<string, unknown>;
  duration_ms?: number;
  error?: string;
  state?: Record<string, unknown>;
  reason?: string;
};

export type PlaybookNodeEvent = PlaybookEvent & {
  payload: PlaybookNodeEventPayload;
};

export type StepRunStatus = "pending" | "running" | "success" | "failed" | "interrupted";

export type StepRunRow = {
  node: string;
  status: StepRunStatus;
  startedAt?: string;
  completedAt?: string;
  duration_ms?: number;
  input_state?: Record<string, unknown>;
  output_state?: Record<string, unknown>;
  error?: string;
  rawEvents: PlaybookEvent[];
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

const SECRET_KEY_PATTERN = /password|token|secret/i;

export function isSecretKey(key: string): boolean {
  return SECRET_KEY_PATTERN.test(key);
}

export function redactStateForDisplay(
  value: Record<string, unknown> | undefined,
): Record<string, unknown> | undefined {
  if (!value) return value;
  if (value._truncated === true) return value;
  const redacted: Record<string, unknown> = {};
  for (const [key, entry] of Object.entries(value)) {
    if (isSecretKey(key)) {
      redacted[key] = "[redacted]";
      continue;
    }
    if (entry && typeof entry === "object" && !Array.isArray(entry)) {
      redacted[key] = redactStateForDisplay(entry as Record<string, unknown>) ?? {};
      continue;
    }
    redacted[key] = entry;
  }
  return redacted;
}

function rowIndex(rows: StepRunRow[], node: string): number {
  return rows.findIndex((row) => row.node === node);
}

export function groupPlaybookEventsByNode(events: PlaybookEvent[]): StepRunRow[] {
  const rows: StepRunRow[] = [];

  for (const event of events) {
    const payload = event.payload as PlaybookNodeEventPayload;
    const node = typeof payload.node === "string" ? payload.node : undefined;
    if (!node) continue;

    let index = rowIndex(rows, node);
    if (index < 0) {
      rows.push({
        node,
        status: "pending",
        rawEvents: [],
      });
      index = rows.length - 1;
    }

    const row = rows[index];
    row.rawEvents.push(event);

    if (event.event_type === "playbook.node.started") {
      row.status = "running";
      row.startedAt = event.timestamp;
      row.input_state =
        (payload.input_state as Record<string, unknown> | undefined) ||
        (payload.state as Record<string, unknown> | undefined);
    }

    if (event.event_type === "playbook.node.completed") {
      row.status = "success";
      row.completedAt = event.timestamp;
      row.duration_ms =
        typeof payload.duration_ms === "number" ? payload.duration_ms : row.duration_ms;
      row.input_state =
        (payload.input_state as Record<string, unknown> | undefined) || row.input_state;
      row.output_state =
        (payload.output_state as Record<string, unknown> | undefined) ||
        (payload.state as Record<string, unknown> | undefined);
    }

    if (event.event_type === "playbook.node.failed") {
      row.status = "failed";
      row.completedAt = event.timestamp;
      row.duration_ms =
        typeof payload.duration_ms === "number" ? payload.duration_ms : row.duration_ms;
      row.input_state =
        (payload.input_state as Record<string, unknown> | undefined) || row.input_state;
      row.error = typeof payload.error === "string" ? payload.error : row.error;
    }

    if (
      event.event_type === "playbook.interrupted" ||
      event.event_type === "playbook.approval.requested"
    ) {
      row.status = "interrupted";
      row.completedAt = event.timestamp;
      row.error =
        typeof payload.reason === "string"
          ? payload.reason
          : row.error || "Interrupted";
    }
  }

  return rows;
}
