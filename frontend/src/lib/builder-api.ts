import { ceApi } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

export type BuilderProject = {
  id: string;
  name: string;
  path: string;
  tech_stack: string[];
  stack_type: string;
  framework?: string;
  status: string;
  keprix_app?: boolean;
  scout_enrolled?: boolean;
};

export type BuilderJob = {
  id: string;
  project_id: string;
  job_type: string;
  instruction: string;
  status: string;
  output?: string;
  diff_summary?: string;
  trajectory_run_id?: string;
  needs_tier3_approval?: boolean;
  approval_reason?: string;
  mutation_id?: string;
  created_at?: string;
};

export type BuilderPatchStep = {
  id: string;
  event: string;
  label: string;
  timestamp?: string;
  diff?: string | null;
  summary?: string;
  needs_approval?: boolean;
  payload?: Record<string, unknown>;
};

export type BuilderTemplate = {
  name: string;
  description: string;
  files: string[];
  implemented?: boolean;
};

export async function fetchBuilderProjects() {
  return parseJson<{ projects: BuilderProject[]; count: number }>(
    await ceApi("/api/builder/projects"),
    "builder projects",
  );
}

export async function scanBuilderProjects() {
  return parseJson<{ projects: BuilderProject[]; count: number }>(
    await ceApi("/api/builder/projects/scan", { method: "POST" }),
    "builder scan",
  );
}

export async function fetchBuilderProject(projectId: string) {
  return parseJson<{ project: BuilderProject; analysis: Record<string, unknown> }>(
    await ceApi(`/api/builder/projects/${encodeURIComponent(projectId)}`),
    "builder project",
  );
}

export async function startBuilderJob(projectId: string, instruction: string) {
  return parseJson<{ job: BuilderJob }>(
    await ceApi(`/api/builder/projects/${encodeURIComponent(projectId)}/build`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ instruction }),
    }),
    "builder build",
  );
}

export async function fetchBuilderJobs(projectId?: string) {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return parseJson<{ jobs: BuilderJob[]; count: number }>(
    await ceApi(`/api/builder/jobs${query}`),
    "builder jobs",
  );
}

export async function fetchBuilderJob(jobId: string) {
  return parseJson<{ job: BuilderJob; log: string; trajectory: BuilderPatchStep[] }>(
    await ceApi(`/api/builder/jobs/${encodeURIComponent(jobId)}`),
    "builder job",
  );
}

export async function fetchBuilderTemplates() {
  return parseJson<{ templates: BuilderTemplate[] }>(
    await ceApi("/api/builder/templates"),
    "builder templates",
  );
}

export async function scaffoldBuilderProject(payload: {
  template: string;
  name: string;
  path: string;
  config?: Record<string, unknown>;
}) {
  return parseJson<{ result: Record<string, unknown>; project: BuilderProject }>(
    await ceApi("/api/builder/scaffold", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "builder scaffold",
  );
}

export function streamBuilderJob(
  jobId: string,
  onEvent: (event: Record<string, unknown>) => void,
  onError?: (error: Error) => void,
): () => void {
  const base = process.env.NEXT_PUBLIC_CE_API_URL || "";
  const source = new EventSource(`${base}/api/builder/jobs/${encodeURIComponent(jobId)}/stream`);
  source.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data) as Record<string, unknown>);
    } catch (err) {
      onError?.(err instanceof Error ? err : new Error("Invalid SSE payload"));
    }
  };
  source.onerror = () => {
    onError?.(new Error("SSE connection error"));
    source.close();
  };
  return () => source.close();
}
