import { ceApi } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

export type PipelineRun = {
  run_id: string;
  pipeline_id: string;
  playbook_run_id?: string | null;
  answer?: string;
  citations?: Array<Record<string, unknown>>;
  route?: string;
  confidence?: number;
  trace?: Array<Record<string, unknown>>;
  evaluation_id?: string | null;
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
  return parseJson<PipelineRun>(
    await ceApi("/api/rag-pipeline/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: payload.user_id || "default",
        source_type: payload.source_type || "plaintext",
        ...payload,
      }),
    }),
    "rag-pipeline-ingest",
  );
}

export async function queryPipeline(payload: {
  question: string;
  pipeline_id?: string;
  source_types?: string[];
  user_id?: string;
}) {
  return parseJson<PipelineRun>(
    await ceApi("/api/rag-pipeline/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: payload.user_id || "default",
        pipeline_id: payload.pipeline_id || "default",
        source_types: payload.source_types || [],
        hybrid: true,
        store_kind: "memory",
        ...payload,
      }),
    }),
    "rag-pipeline-query",
  );
}

export async function fetchPipelineRuns(pipelineId?: string) {
  const suffix = pipelineId ? `?pipeline_id=${encodeURIComponent(pipelineId)}` : "";
  return parseJson<{ runs: PipelineRun[] }>(
    await ceApi(`/api/rag-pipeline/runs${suffix}`),
    "rag-pipeline-runs",
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
  return parseJson<{ ready: boolean; checks: Array<Record<string, unknown>> }>(
    await ceApi(`/api/rag-pipeline/deployment/${encodeURIComponent(pipelineId)}`),
    "rag-pipeline-deployment",
  );
}

export async function listPipelineStores() {
  return parseJson<{ stores: Array<Record<string, string>> }>(
    await ceApi("/api/rag-pipeline/stores"),
    "rag-pipeline-stores",
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
  return parseJson<{ run_id: string; documents_ingested: number; errors?: Array<{ id: string; error: string }> }>(
    await ceApi("/api/rag-pipeline/ingest/notion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: payload.user_id || "default",
        store_kind: payload.store_kind || "memory",
        ...payload,
      }),
    }),
    "rag-pipeline-ingest-notion",
  );
}
