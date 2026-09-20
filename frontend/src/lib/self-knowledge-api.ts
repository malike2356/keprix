import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

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

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json() as Promise<T>;
}

export async function fetchSelfKnowledgeStatus(): Promise<SelfKnowledgeStatus> {
  return parseJson(
    await ceApi(`${BASE}/status`),
    "Failed to load self-knowledge status",
  );
}

export async function triggerIngest(opts?: {
  includeCodebase?: boolean;
  includeCodbase?: boolean;
  includeDocs?: boolean;
}): Promise<{ status: string }> {
  const params = new URLSearchParams();
  const includeCodebase = opts?.includeCodebase ?? opts?.includeCodbase;
  if (includeCodebase !== undefined) params.set("include_codebase", String(includeCodebase));
  if (opts?.includeDocs !== undefined) params.set("include_docs", String(opts.includeDocs));
  return parseJson(await ceApi(`${BASE}/ingest?${params}`, { method: "POST" }), "Failed to start ingest");
}

export async function triggerIngestAndWait(opts?: {
  includeCodebase?: boolean;
  includeDocs?: boolean;
  maxFiles?: number;
}): Promise<IngestResult> {
  const params = new URLSearchParams();
  if (opts?.includeCodebase !== undefined) params.set("include_codebase", String(opts.includeCodebase));
  if (opts?.includeDocs !== undefined) params.set("include_docs", String(opts.includeDocs));
  if (opts?.maxFiles !== undefined) params.set("max_files", String(opts.maxFiles));
  return parseJson(await ceApi(`${BASE}/ingest/wait?${params}`, { method: "POST" }), "Failed to ingest");
}

export async function searchSelfKnowledge(query: string, limit = 8): Promise<SearchResponse> {
  return parseJson(
    await ceApi(`${BASE}/search`, {
      method: "POST",
      body: JSON.stringify({ query, limit, hybrid: true }),
    }),
    "Search failed",
  );
}
