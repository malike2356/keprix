import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type MlExperiment = {
  experiment_id: string;
  name: string;
  task_type?: string;
  dataset_id?: string | null;
  parameters?: Record<string, unknown>;
  created_at?: string;
};

export type MlRun = {
  run_id: string;
  experiment_id: string;
  status?: string;
  metrics?: Record<string, unknown>;
  artifact_path?: string | null;
  created_at?: string;
};

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

export async function fetchMlExperiments() {
  return parseJson<{ items: MlExperiment[] }>(
    await ceApi("/api/ml/experiments"),
    "Failed to load ML experiments",
  );
}

export async function fetchMlRuns(experimentId?: string) {
  return parseJson<{ items: MlRun[] }>(
    await ceApi(`/api/ml/runs${qs({ experiment_id: experimentId })}`),
    "Failed to load ML runs",
  );
}

export async function fetchMlModelRegistry() {
  return parseJson<{ items: MlRun[] }>(
    await ceApi("/api/ml/model-registry"),
    "Failed to load model registry",
  );
}

export async function createMlExperiment(body: {
  name: string;
  task_type: string;
  dataset_id?: string;
  parameters?: Record<string, unknown>;
}) {
  return parseJson<{ experiment: MlExperiment }>(
    await ceApi("/api/ml/experiments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to create experiment",
  );
}

export async function createMlRun(body: {
  experiment_id: string;
  metrics?: Record<string, unknown>;
}) {
  return parseJson<{ run: MlRun }>(
    await ceApi("/api/ml/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to create run",
  );
}
