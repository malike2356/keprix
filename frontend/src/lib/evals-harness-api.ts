import { ceApi } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

export type EvalTaskResult = {
  task_id: string;
  passed: boolean;
  reason?: string | null;
  output?: string;
  trace_id?: string | null;
  expected?: string | null;
};

export type EvalSuiteResult = {
  suite: string;
  pass_rate: number;
  passed: number;
  total: number;
  avg_cost_usd: number;
  avg_latency_ms: number;
  tasks: EvalTaskResult[];
};

export type EvalTraceSpan = {
  name: string;
  event: string;
  timestamp?: string;
  payload?: Record<string, unknown>;
};

export type EvalTrace = {
  trace_id: string;
  spans: EvalTraceSpan[];
  linked_run_ids: Record<string, string>;
  expected?: string | null;
  actual?: string | null;
  task_id?: string | null;
  suite?: string | null;
  reason?: string | null;
};

export type ReleaseGate = {
  passed: boolean;
  pass_rate: number;
  min_pass_rate: number;
  failures: string[];
};

export async function fetchEvalSuites() {
  return parseJson<{ suites: string[] }>(await ceApi("/api/evals/suites"), "eval suites");
}

export async function runEvalSuite(suiteName: string) {
  return parseJson<EvalSuiteResult>(
    await ceApi(`/api/evals/run/${encodeURIComponent(suiteName)}`, { method: "POST" }),
    "run eval suite",
  );
}

export async function runAllEvals() {
  return parseJson<{ release_gate: ReleaseGate; suites: EvalSuiteResult[] }>(
    await ceApi("/api/evals/run", { method: "POST" }),
    "run all evals",
  );
}

export async function runReleaseGate(minPassRate = 0.9) {
  return parseJson<{ release_gate: ReleaseGate; report_json: string }>(
    await ceApi("/api/evals/release-gate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ min_pass_rate: minPassRate }),
    }),
    "release gate",
  );
}

export async function fetchEvalTrace(traceId: string) {
  return parseJson<EvalTrace>(
    await ceApi(`/api/evals/traces/${encodeURIComponent(traceId)}`),
    "eval trace",
  );
}
