import { buildApiHeaders, ceApi, getApiBaseUrl, parseApiErrorMessage } from "@/lib/ce-api";

export type ResearchDepth = "quick" | "standard" | "deep";
export type NotebookResearchDepth = "notebook" | "notebook-external";

export type ResearchJob = {
  job_id: string;
  query: string;
  depth: string;
  status: string;
  progress_pct?: number;
  current_step?: string | null;
  sub_questions: string[];
  sources: Array<{ title?: string; url?: string; snippet?: string }>;
  model_used?: string | null;
  tokens_used?: number;
  started_at?: string;
  completed_at?: string | null;
  error_message?: string | null;
};

export type ResearchStoredEvent = {
  id: number;
  task_id: string;
  event_type: string;
  payload?: Record<string, unknown>;
  emitted_at?: string;
};

export type ResearchStreamEvent = {
  type: string;
  status?: string;
  sub_questions?: string[];
  question?: string;
  count?: number;
  url?: string;
  title?: string;
  preview?: string;
  error?: string;
};

export function storedEventToStream(event: ResearchStoredEvent): ResearchStreamEvent {
  return {
    type: event.event_type,
    ...(event.payload || {}),
  } as ResearchStreamEvent;
}

export function isTerminalResearchStatus(status: string): boolean {
  return status === "complete" || status === "failed" || status === "error" || status === "cancelled";
}

export type ResearchExportFormat = "pdf" | "html" | "markdown" | "docx";

export type NotebookSource = {
  id?: string;
  kind: "text" | "url" | "file" | "session_export";
  ref: string;
  title?: string;
  excerpt?: string | null;
};

export type NotebookResearchJob = {
  job_id: string;
  depth: NotebookResearchDepth;
  query: string;
  sources: NotebookSource[];
  report_md?: string | null;
  citations: Array<Record<string, unknown>>;
  status: string;
  external_notebook_id?: string | null;
  error?: string | null;
  export_path?: string | null;
};

export type NotebookResearchConfig = {
  enabled: boolean;
  native_max_sources: number;
  external_enabled: boolean;
  graph_ingest_enabled: boolean;
};

export async function fetchNotebookResearchConfig(): Promise<NotebookResearchConfig> {
  const response = await ceApi("/api/research/notebook/config");
  if (!response.ok) {
    return { enabled: false, native_max_sources: 20, external_enabled: false, graph_ingest_enabled: false };
  }
  return response.json();
}

export async function normalizeNotebookSource(source: Omit<NotebookSource, "id">): Promise<NotebookSource> {
  const response = await ceApi("/api/research/notebook/sources", {
    method: "POST",
    body: JSON.stringify(source),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Could not add source"));
  }
  const data = (await response.json()) as { source: NotebookSource };
  return data.source;
}

export async function startNotebookResearch(
  query: string,
  depth: NotebookResearchDepth,
  sources: NotebookSource[],
): Promise<NotebookResearchJob> {
  const response = await ceApi("/api/research/notebook", {
    method: "POST",
    body: JSON.stringify({ query, depth, sources }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Notebook research failed"));
  }
  const data = (await response.json()) as { job: NotebookResearchJob };
  return data.job;
}

export async function exportNotebookResearch(jobId: string, path?: string): Promise<{ path: string }> {
  const response = await ceApi(`/api/research/notebook/${encodeURIComponent(jobId)}/export`, {
    method: "POST",
    body: JSON.stringify({ path }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Notebook export failed"));
  }
  return response.json();
}

export async function sendNotebookReportToGraph(job: NotebookResearchJob): Promise<void> {
  const response = await ceApi("/api/brain/graphiti/ingest", {
    method: "POST",
    body: JSON.stringify({
      source_type: "research",
      source_ref: job.job_id,
      content: job.report_md || "",
    }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Graph ingest failed"));
  }
}

export async function startResearch(query: string, depth: ResearchDepth, model?: string) {
  const response = await ceApi("/api/research/start", {
    method: "POST",
    body: JSON.stringify({ query, depth, model }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { detail?: string }).detail || "Failed to start research");
  }
  return response.json() as Promise<{ job_id: string; status: string }>;
}

export async function fetchResearchJob(jobId: string): Promise<ResearchJob> {
  const response = await ceApi(`/api/research/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error("Failed to load research job");
  }
  return response.json();
}

export async function fetchResearchReport(jobId: string): Promise<string> {
  const response = await ceApi(`/api/research/jobs/${jobId}/report`);
  if (!response.ok) {
    throw new Error("Report not ready");
  }
  const data = (await response.json()) as { report_markdown: string };
  return data.report_markdown;
}

export async function fetchResearchPresets(): Promise<
  Record<string, { model: string; note: string }>
> {
  const response = await ceApi("/api/playbook/research-presets");
  if (!response.ok) {
    return {};
  }
  return response.json();
}

export async function fetchResearchJobs(): Promise<ResearchJob[]> {
  const response = await ceApi("/api/research/jobs");
  if (!response.ok) {
    return [];
  }
  const data = (await response.json()) as { jobs: ResearchJob[] };
  return data.jobs;
}

export async function deleteResearchJob(jobId: string): Promise<void> {
  const response = await ceApi(`/api/research/jobs/${encodeURIComponent(jobId)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { detail?: string }).detail || "Failed to delete research run");
  }
}

export async function fetchResearchEvents(jobId: string, sinceId = 0): Promise<ResearchStoredEvent[]> {
  const suffix = sinceId > 0 ? `?since_id=${sinceId}` : "";
  const response = await ceApi(`/api/research/tasks/${jobId}/events${suffix}`);
  if (!response.ok) {
    throw new Error("Failed to load research events");
  }
  const data = (await response.json()) as { events: ResearchStoredEvent[] };
  return data.events || [];
}

export async function watchResearchJob(
  jobId: string,
  onEvent: (event: ResearchStreamEvent) => void,
  signal?: AbortSignal,
): Promise<ResearchJob> {
  const job = await fetchResearchJob(jobId);
  if (isTerminalResearchStatus(job.status)) {
    const stored = await fetchResearchEvents(jobId);
    for (const row of stored) {
      onEvent(storedEventToStream(row));
    }
    onEvent({ type: "complete", status: job.status });
    return job;
  }

  await streamResearchEvents(jobId, onEvent, signal);
  return fetchResearchJob(jobId);
}

export async function streamResearchEvents(
  jobId: string,
  onEvent: (event: ResearchStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const url = `${getApiBaseUrl()}/api/research/jobs/${jobId}/stream`;
  const response = await fetch(url, {
    headers: buildApiHeaders(),
    credentials: "include",
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error("Failed to open research stream");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part
        .split("\n")
        .find((row) => row.startsWith("data: "));
      if (!line) {
        continue;
      }
      try {
        onEvent(JSON.parse(line.slice(6)) as ResearchStreamEvent);
      } catch {
        // ignore malformed chunks
      }
    }
  }
}

export async function downloadResearchExport(
  jobId: string,
  format: ResearchExportFormat,
  options?: { includeCover?: boolean },
): Promise<{ filename: string; fallback?: string }> {
  const params = new URLSearchParams({ format });
  if (options?.includeCover === false) {
    params.set("include_cover", "false");
  }
  const response = await fetch(
    `${getApiBaseUrl()}/api/research/jobs/${encodeURIComponent(jobId)}/export?${params.toString()}`,
    {
      headers: buildApiHeaders(),
      credentials: "include",
    },
  );
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = parseApiErrorMessage(payload, "Export failed");
    if (response.status === 404 && detail === "Not Found") {
      throw new Error(
        "Export API is not available on the server. Restart the Keprix backend and try again.",
      );
    }
    if (response.status === 409) {
      throw new Error(detail === "Not Found" ? "Report not ready yet." : detail);
    }
    throw new Error(detail);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename =
    match?.[1] || `research-${jobId}.${format === "markdown" ? "md" : format}`;
  const fallback = response.headers.get("X-Export-Fallback") || undefined;
  const renderer = response.headers.get("X-PDF-Renderer") || undefined;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  return {
    filename,
    fallback: fallback || (renderer === "text-fallback" ? "Install weasyprint for styled PDFs." : undefined),
  };
}
