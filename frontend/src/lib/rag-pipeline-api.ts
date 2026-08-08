import { ceApi } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

let cachedUserId: string | null | undefined;

async function resolveUserId(explicit?: string): Promise<string> {
  if (explicit && explicit !== "default") {
    return explicit;
  }
  if (cachedUserId) {
    return cachedUserId;
  }
  try {
    const response = await ceApi("/api/auth/me");
    if (response.ok) {
      const me = (await response.json()) as { id?: string; username?: string; user?: { id?: string } };
      const id = String(me.id || me.user?.id || me.username || "").trim();
      if (id) {
        cachedUserId = id;
        return id;
      }
    }
  } catch {
    // fall through
  }
  cachedUserId = null;
  return "anonymous";
}

export type PipelineRun = {
  run_id: string;
  pipeline_id: string;
  playbook_run_id?: string | null;
  query?: string;
  answer?: string;
  citations?: Array<Record<string, unknown>>;
  route?: string;
  confidence?: number;
  trace?: Array<Record<string, unknown>>;
  evaluation_id?: string | null;
  latency_ms?: Record<string, number>;
  metadata?: Record<string, unknown>;
};

export type EvaluationReport = {
  eval_id: string;
  pipeline_id: string;
  retrieval_precision: number;
  citation_faithfulness: number;
  answer_completeness: number;
  hallucination_risk: number;
  latency_ms: number;
  cost_units: number;
};

export async function ingestPipelineDocument(payload: {
  source_id: string;
  content: string;
  source_type?: string;
  pipeline_id?: string;
  store_kind?: string;
  user_id?: string;
}) {
  const user_id = await resolveUserId(payload.user_id);
  return parseJson<PipelineRun>(
    await ceApi("/api/rag-pipeline/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_type: payload.source_type || "plaintext",
        ...payload,
        user_id,
      }),
    }),
    "rag-pipeline-ingest",
  );
}

export async function queryPipeline(payload: {
  question: string;
  pipeline_id?: string;
  source_types?: string[];
  store_kind?: string;
  user_id?: string;
}) {
  const user_id = await resolveUserId(payload.user_id);
  const body: Record<string, unknown> = {
    question: payload.question,
    pipeline_id: payload.pipeline_id,
    source_types: payload.source_types || [],
    hybrid: true,
    user_id,
  };
  if (payload.store_kind) {
    body.store_kind = payload.store_kind;
  }
  return parseJson<PipelineRun>(
    await ceApi("/api/rag-pipeline/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "rag-pipeline-query",
  );
}

export async function fetchPipelineEvaluations(pipelineId?: string) {
  const suffix = pipelineId ? `?pipeline_id=${encodeURIComponent(pipelineId)}` : "";
  return parseJson<{ evaluations: EvaluationReport[] }>(
    await ceApi(`/api/rag-pipeline/evaluations${suffix}`),
    "rag-pipeline-evals",
  );
}

export async function fetchDeploymentStatus(pipelineId: string) {
  return parseJson<{ ready: boolean; checks: Array<Record<string, unknown>>; plain?: string }>(
    await ceApi(`/api/rag-pipeline/deployment/${encodeURIComponent(pipelineId)}`),
    "rag-pipeline-deployment",
  );
}

export async function listPipelineStores() {
  return parseJson<{ stores: Array<Record<string, string | number>> }>(
    await ceApi("/api/rag-pipeline/stores"),
    "rag-pipeline-stores",
  );
}

export async function fetchRagConfig() {
  return parseJson<{ default_pipeline_id: string; pipelines: string[] }>(
    await ceApi("/api/rag-pipeline/config"),
    "rag-pipeline-config",
  );
}

export async function createPipeline(pipelineId: string, storeKind = "memory") {
  return parseJson<{ pipeline_id: string; store_kind: string; ok: boolean }>(
    await ceApi("/api/rag-pipeline/pipelines", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pipeline_id: pipelineId, store_kind: storeKind }),
    }),
    "rag-pipeline-create",
  );
}

export async function ingestNotionPipeline(payload: {
  pipeline_id: string;
  store_kind?: string;
  page_ids?: string[];
  database_ids?: string[];
  token?: string;
  user_id?: string;
}) {
  const user_id = await resolveUserId(payload.user_id);
  return parseJson<{ run_id: string; documents_ingested: number; errors?: Array<{ id: string; error: string }> }>(
    await ceApi("/api/rag-pipeline/ingest/notion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        store_kind: payload.store_kind || "memory",
        ...payload,
        user_id,
      }),
    }),
    "rag-pipeline-ingest-notion",
  );
}

export async function ingestPipelinePath(payload: {
  path: string;
  pipeline_id?: string;
  store_kind?: string;
  vault_relative?: boolean;
  user_id?: string;
}) {
  const user_id = await resolveUserId(payload.user_id);
  return parseJson<PipelineRun>(
    await ceApi("/api/rag-pipeline/ingest/path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, user_id }),
    }),
    "rag-pipeline-ingest-path",
  );
}

export async function ingestPipelineUrl(payload: {
  url: string;
  pipeline_id?: string;
  store_kind?: string;
  user_id?: string;
}) {
  const user_id = await resolveUserId(payload.user_id);
  return parseJson<PipelineRun>(
    await ceApi("/api/rag-pipeline/ingest/url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, user_id }),
    }),
    "rag-pipeline-ingest-url",
  );
}

export async function ingestPipelineUpload(payload: {
  file: File;
  pipeline_id: string;
  store_kind?: string;
}) {
  const user_id = await resolveUserId();
  const form = new FormData();
  form.append("file", payload.file);
  form.append("pipeline_id", payload.pipeline_id);
  if (payload.store_kind) {
    form.append("store_kind", payload.store_kind);
  }
  form.append("user_id", user_id);
  return parseJson<PipelineRun>(
    await ceApi("/api/rag-pipeline/ingest/file", { method: "POST", body: form }),
    "rag-pipeline-ingest-file",
  );
}

export async function fetchPipelineRuns(pipelineId?: string, q?: string) {
  const search = new URLSearchParams();
  if (pipelineId) search.set("pipeline_id", pipelineId);
  if (q) search.set("q", q);
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return parseJson<{ runs: PipelineRun[] }>(
    await ceApi(`/api/rag-pipeline/runs${suffix}`),
    "rag-pipeline-runs",
  );
}
