const BASE = "/api/self-knowledge";

export interface SourceEntry {
  source_type: string;
  source_id: string;
  chunk_count: number;
}

export interface SelfKnowledgeStatus {
  indexed: boolean;
  document_count: number;
  total_chunks: number;
  user_id?: string;
  source_type?: string;
  sources?: SourceEntry[];
  error?: string;
}

export interface IngestResult {
  synthetic_docs: number;
  synthetic_chunks: number;
  full_index?: {
    docs_indexed: number;
    doc_chunks: number;
    capability_chunks: number;
    codebase_files: number;
    codebase_chunks: number;
    total_chunks: number;
  } | null;
  errors: string[];
  total_chunks: number;
}

export interface SearchResult {
  content: string;
  source: string;
  score?: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  formatted: string;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function fetchSelfKnowledgeStatus(): Promise<SelfKnowledgeStatus> {
  return apiFetch<SelfKnowledgeStatus>(`${BASE}/status`);
}

export function triggerIngest(opts?: {
  includeCodbase?: boolean;
  includeDocs?: boolean;
}): Promise<{ status: string }> {
  const params = new URLSearchParams();
  if (opts?.includeCodbase !== undefined)
    params.set("include_codebase", String(opts.includeCodbase));
  if (opts?.includeDocs !== undefined)
    params.set("include_docs", String(opts.includeDocs));
  return apiFetch<{ status: string }>(`${BASE}/ingest?${params}`, { method: "POST" });
}

export function triggerIngestAndWait(opts?: {
  includeCodebase?: boolean;
  includeDocs?: boolean;
  maxFiles?: number;
}): Promise<IngestResult> {
  const params = new URLSearchParams();
  if (opts?.includeCodebase !== undefined)
    params.set("include_codebase", String(opts.includeCodebase));
  if (opts?.includeDocs !== undefined)
    params.set("include_docs", String(opts.includeDocs));
  if (opts?.maxFiles !== undefined) params.set("max_files", String(opts.maxFiles));
  return apiFetch<IngestResult>(`${BASE}/ingest/wait?${params}`, { method: "POST" });
}

export function searchSelfKnowledge(query: string, limit = 8): Promise<SearchResponse> {
  return apiFetch<SearchResponse>(`${BASE}/search`, {
    method: "POST",
    body: JSON.stringify({ query, limit, hybrid: true }),
  });
}
