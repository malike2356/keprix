import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
}

export async function fetchBenchmarkSuites() {
  return parseJson<{ suites: string[]; workflows?: string[] }>(
    await ceApi("/api/evals/benchmarks/suites"),
    "Failed to load benchmark suites",
  );
}

export async function runBenchmarkAll() {
  return parseJson<Record<string, unknown>>(
    await ceApi("/api/evals/benchmarks/run", { method: "POST" }),
    "Failed to run benchmarks",
  );
}

export async function runBenchmarkSuite(suite: string) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/evals/benchmarks/run/${encodeURIComponent(suite)}`, { method: "POST" }),
    "Failed to run suite",
  );
}

export async function fetchBenchmarkBaseline() {
  return parseJson<{ baseline: Record<string, unknown> }>(
    await ceApi("/api/evals/benchmarks/baseline"),
    "Failed to load baseline",
  );
}

export async function runBenchmarkRegression() {
  return parseJson<Record<string, unknown>>(
    await ceApi("/api/evals/benchmarks/regression", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }),
    "Failed to run regression",
  );
}
