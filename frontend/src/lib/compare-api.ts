import { ceApi } from "@/lib/ce-api";

export type CompareModel = {
  id: string;
  provider: string;
  name: string;
  label?: string;
};

export type CompareStartResult = {
  comparison_id: string;
  response_a: string;
  response_b: string;
  latency_ms_a: number;
  latency_ms_b: number;
};

export type CompareStartOptions = {
  prompt: string;
  modelA?: string;
  modelB?: string;
  randomModels?: boolean;
};

export async function fetchCompareModels(): Promise<CompareModel[]> {
  const response = await ceApi("/api/compare/models");
  if (!response.ok) {
    return [];
  }
  const data = (await response.json()) as { models: CompareModel[] };
  return data.models;
}

export async function startComparison({
  prompt,
  modelA,
  modelB,
  randomModels = true,
}: CompareStartOptions): Promise<CompareStartResult> {
  const response = await ceApi("/api/compare/start", {
    method: "POST",
    body: JSON.stringify({
      prompt,
      model_a: modelA,
      model_b: modelB,
      random_models: randomModels,
    }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { detail?: string }).detail || "Comparison failed");
  }
  return response.json();
}

export async function voteComparison(
  comparisonId: string,
  winner: "a" | "b" | "tie",
): Promise<{
  winner: string;
  model_a: string;
  model_b: string;
  latency_ms_a: number | null;
  latency_ms_b: number | null;
}> {
  const response = await ceApi(`/api/compare/${comparisonId}/vote`, {
    method: "POST",
    body: JSON.stringify({ winner }),
  });
  if (!response.ok) {
    throw new Error("Failed to record vote");
  }
  return response.json();
}

export type CompareHistoryEntry = {
  id: string;
  prompt: string;
  model_a: string;
  model_b: string;
  winner: string | null;
  voted_at: string | null;
  created_at: string;
  latency_ms_a: number | null;
  latency_ms_b: number | null;
};

export type LeaderboardPairRow = {
  model_a: string;
  model_b: string;
  comparisons: number;
  a_wins: number;
  b_wins: number;
  ties: number;
  a_win_rate_pct: number;
  b_win_rate_pct: number;
  tie_rate_pct: number;
};

export type LeaderboardModelRow = {
  model_id: string;
  wins: number;
  losses: number;
  ties: number;
  comparisons: number;
  win_rate_pct: number;
};

export type CompareLeaderboard = {
  pairs: LeaderboardPairRow[];
  models: LeaderboardModelRow[];
};

export async function fetchCompareHistory(): Promise<CompareHistoryEntry[]> {
  const response = await ceApi("/api/compare/history");
  if (!response.ok) {
    return [];
  }
  return response.json();
}

export async function fetchCompareLeaderboard(): Promise<CompareLeaderboard> {
  const response = await ceApi("/api/compare/leaderboard");
  if (!response.ok) {
    return { pairs: [], models: [] };
  }
  return response.json();
}
