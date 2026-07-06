import useSWR from "swr";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type MutationTier = "tool" | "prompt" | "code";
export type MutationStatus =
  | "staged"
  | "approved"
  | "quarantined"
  | "pruned"
  | "expired"
  | "rolled_back"
  | "rejected";

export type MutationRecord = {
  id: string;
  recorded_at: string;
  workspace_id: string;
  tier: MutationTier | string;
  trigger: string;
  status: MutationStatus | string;
  name: string;
  description: string | null;
  approved_by: string | null;
  approved_at: string | null;
  quality_score: number | null;
  use_count: number;
  last_used_at: string | null;
  metadata: Record<string, unknown>;
  after_value?: string | null;
  before_value?: string | null;
};

export type PromptVersion = {
  id: string;
  workspace_id: string;
  prompt_key: string;
  version: number;
  content: string;
  is_active: boolean;
  created_at: string;
  created_by: string;
  mutation_id: string | null;
  notes: string | null;
};

export type QualitySample = {
  outcome: string;
  score: number;
  run_id: string | null;
  task_id: string | null;
  feedback: string | null;
  sampled_at: string;
};

export type CompoundingMetrics = {
  workspace_id: string;
  total_mutations: number;
  active_mutations: number;
  promoted_mutations: number;
  avg_quality_score: number;
  total_tool_uses_by_generated: number;
  mutation_age_days: number;
  divergence_score: number;
  tools_contributed: number;
  prompts_evolved: number;
  code_mutations_merged: number;
};

export type MutationStats = {
  counts: Record<string, Record<string, number>>;
  total: number;
  staged: number;
  active_tools: number;
  evolved_prompts: number;
  code_merged: number;
};

export type PruneReport = {
  pruned_tools: string[];
  pruned_prompts: string[];
  pruned_code: string[];
  total_pruned: number;
  space_reclaimed_bytes: number;
  dry_run?: boolean;
};

export type MutationHistoryFilters = {
  tier?: string;
  status?: string;
  trigger?: string;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  perPage?: number;
};

export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  per_page: number;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json() as Promise<T>;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export async function fetchMutationQueue(): Promise<Paginated<MutationRecord>> {
  return parseJson(await ceApi("/api/mutation/queue"), "mutation queue");
}

export async function fetchMutationStats(): Promise<MutationStats> {
  return parseJson(await ceApi("/api/mutation/stats"), "mutation stats");
}

export async function fetchGeneratedTools(
  page: number,
  status?: string,
): Promise<Paginated<MutationRecord>> {
  return parseJson(
    await ceApi(`/api/mutation/tools${buildQuery({ page, per_page: 20, status, tier: "tool" })}`),
    "generated tools",
  );
}

export async function fetchPromptVersions(page = 1): Promise<Paginated<PromptVersion>> {
  return parseJson(
    await ceApi(`/api/mutation/prompts${buildQuery({ page, per_page: 100 })}`),
    "prompt versions",
  );
}

export async function fetchPromptHistory(promptKey: string): Promise<{ items: PromptVersion[] }> {
  return parseJson(await ceApi(`/api/mutation/prompts/${encodeURIComponent(promptKey)}/history`), "prompt history");
}

export async function fetchCodeMutations(page: number, status?: string): Promise<Paginated<MutationRecord>> {
  return parseJson(
    await ceApi(`/api/mutation/code${buildQuery({ page, per_page: 20, status })}`),
    "code mutations",
  );
}

export async function fetchMutationHistory(
  filters: MutationHistoryFilters,
): Promise<Paginated<MutationRecord>> {
  return parseJson(
    await ceApi(
      `/api/mutation/history${buildQuery({
        tier: filters.tier,
        status: filters.status,
        trigger: filters.trigger,
        date_from: filters.dateFrom,
        date_to: filters.dateTo,
        page: filters.page ?? 1,
        per_page: filters.perPage ?? 20,
      })}`,
    ),
    "mutation history",
  );
}

export async function fetchMutationDetail(id: string): Promise<MutationRecord> {
  return parseJson(await ceApi(`/api/mutation/tools/${id}`), "mutation detail");
}

export async function fetchToolSource(id: string): Promise<{ source_code: string; name: string }> {
  return parseJson(await ceApi(`/api/mutation/tools/${id}/source`), "tool source");
}

export async function fetchCodeDiff(id: string): Promise<{ diff: string }> {
  return parseJson(await ceApi(`/api/mutation/code/${id}/diff`), "code diff");
}

export async function fetchCodeTestOutput(id: string): Promise<{
  test_output: string | null;
  test_passed: boolean | null;
}> {
  return parseJson(await ceApi(`/api/mutation/code/${id}/test-output`), "code test output");
}

export async function fetchQualityHistory(mutationId: string): Promise<{
  mutation_id: string;
  quality_score: number | null;
  use_count: number;
  samples: QualitySample[];
}> {
  return parseJson(await ceApi(`/api/mutation/quality/${mutationId}`), "quality history");
}

export async function fetchCompoundingMetrics(): Promise<CompoundingMetrics> {
  return parseJson(await ceApi("/api/mutation/compounding"), "compounding metrics");
}

export async function approveMutation(id: string, tier: string, promptKey?: string): Promise<void> {
  let path = `/api/mutation/tools/${id}/approve`;
  if (tier === "code") {
    path = `/api/mutation/code/${id}/approve`;
  } else if (tier === "prompt" && promptKey) {
    path = `/api/mutation/prompts/${encodeURIComponent(promptKey)}/approve`;
  }
  await parseJson(await ceApi(path, { method: "POST" }), "approve mutation");
}

export async function rejectMutation(id: string, tier: string, reason: string): Promise<void> {
  const path = tier === "code" ? `/api/mutation/code/${id}/reject` : `/api/mutation/tools/${id}/reject`;
  await parseJson(
    await ceApi(path, { method: "POST", body: JSON.stringify({ reason }) }),
    "reject mutation",
  );
}

export async function rollbackMutation(id: string, tier: string, promptKey?: string): Promise<void> {
  if (tier === "prompt" && promptKey) {
    await parseJson(
      await ceApi(`/api/mutation/prompts/${encodeURIComponent(promptKey)}/rollback`, { method: "POST" }),
      "rollback prompt",
    );
    return;
  }
  const path = tier === "code" ? `/api/mutation/code/${id}/rollback` : `/api/mutation/tools/${id}/rollback`;
  await parseJson(await ceApi(path, { method: "POST" }), "rollback mutation");
}

export async function activatePromptVersion(versionId: string): Promise<void> {
  await parseJson(
    await ceApi(`/api/mutation/prompts/versions/${versionId}/activate`, { method: "POST" }),
    "activate prompt version",
  );
}

export async function triggerSynthesis(
  toolName: string,
  description: string,
): Promise<{ id: string }> {
  return parseJson(
    await ceApi("/api/mutation/synthesize", {
      method: "POST",
      body: JSON.stringify({ tool_name: toolName, description }),
    }),
    "trigger synthesis",
  );
}

export async function triggerPrune(dryRun: boolean): Promise<PruneReport> {
  const path = dryRun ? "/api/mutation/prune/dry-run" : "/api/mutation/prune";
  return parseJson(await ceApi(path, { method: "POST" }), "prune mutations");
}

export function useMutationQueue() {
  return useSWR("mutation-queue", fetchMutationQueue, { refreshInterval: 30_000 });
}

export function useMutationStats() {
  return useSWR("mutation-stats", fetchMutationStats, { refreshInterval: 30_000 });
}

export function useGeneratedTools(page: number, status?: string) {
  return useSWR(["mutation-tools", page, status], () => fetchGeneratedTools(page, status));
}

export function usePromptVersions() {
  return useSWR("mutation-prompts", () => fetchPromptVersions(1));
}

export function usePromptHistory(promptKey: string | null) {
  return useSWR(promptKey ? ["mutation-prompt-history", promptKey] : null, () =>
    promptKey ? fetchPromptHistory(promptKey) : null,
  );
}

export function useCodeMutations(page: number, status?: string) {
  return useSWR(["mutation-code", page, status], () => fetchCodeMutations(page, status));
}

export function useMutationHistory(filters: MutationHistoryFilters) {
  return useSWR(["mutation-history", filters], () => fetchMutationHistory(filters));
}

export function useMutationDetail(id: string | null) {
  return useSWR(id ? ["mutation-detail", id] : null, () => (id ? fetchMutationDetail(id) : null));
}

export function useQualityHistory(mutationId: string | null) {
  return useSWR(mutationId ? ["mutation-quality", mutationId] : null, () =>
    mutationId ? fetchQualityHistory(mutationId) : null,
  );
}

export function useCompoundingMetrics() {
  return useSWR("mutation-compounding", fetchCompoundingMetrics);
}
