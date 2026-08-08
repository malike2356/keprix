import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type LocalJob = {
  job_id: string;
  workspace_id?: string;
  job_type: string;
  status: string;
  payload?: Record<string, unknown>;
  claimed_by?: string | null;
  retry_count?: number;
  consecutive_failures?: number;
  dead_letter_reason?: string | null;
  created_at?: string;
  updated_at?: string;
  heartbeat_at?: string | null;
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

export async function fetchLocalJobs(status?: string) {
  return parseJson<{ items: LocalJob[] }>(
    await ceApi(`/api/jobs${qs({ status })}`),
    "Failed to load jobs",
  );
}

export async function cancelLocalJob(jobId: string) {
  return parseJson<{ job: LocalJob }>(
    await ceApi(`/api/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" }),
    "Failed to cancel job",
  );
}

export async function retryLocalJob(jobId: string) {
  return parseJson<{ job: LocalJob }>(
    await ceApi(`/api/jobs/${encodeURIComponent(jobId)}/retry`, { method: "POST" }),
    "Failed to retry job",
  );
}

export function relatedObjectHref(job: LocalJob): string | null {
  const payload = job.payload || {};
  const discoveryId = payload.discovery_job_id || payload.crm_job_id || payload.job_id;
  if (job.job_type.includes("discovery") || payload.adapter) {
    const id = String(discoveryId || job.job_id);
    return `/crm/jobs/${encodeURIComponent(id)}`;
  }
  if (job.job_type.includes("sheet") || payload.sheet_job_id) {
    return "/crm/enrich";
  }
  if (job.job_type.includes("builder") || payload.builder_job_id) {
    return "/builder";
  }
  return null;
}
