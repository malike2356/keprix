import type { GraphNode } from "@/types/brain-graph";

export type BrainHealthReport = {
  workspace_id: string;
  generated_at: string;
  total_nodes: number;
  nodes_by_kind: Record<string, number>;
  total_edges: number;
  edges_by_relation: Record<string, number>;
  orphan_nodes: GraphNode[];
  orphan_count: number;
  stale_nodes: GraphNode[];
  stale_count: number;
  hub_nodes: GraphNode[];
  duplicate_groups: GraphNode[][];
  duplicate_pairs: Array<{
    left: GraphNode;
    right: GraphNode;
    similarity: number;
  }>;
  coverage_gaps: string[];
  avg_memory_age_days: number;
  health_score: number;
  health_label: "Excellent" | "Good" | "Needs attention" | "Poor";
};

export type BrainHealthFlags = {
  orphanIds: Set<string>;
  staleIds: Set<string>;
  hubIds: Set<string>;
  duplicateIds: Set<string>;
};

export function healthFlagsFromReport(report: BrainHealthReport | null): BrainHealthFlags {
  const orphanIds = new Set(report?.orphan_nodes.map((node) => `${node.kind}:${node.id}`) ?? []);
  const staleIds = new Set(report?.stale_nodes.map((node) => `${node.kind}:${node.id}`) ?? []);
  const hubIds = new Set(report?.hub_nodes.map((node) => `${node.kind}:${node.id}`) ?? []);
  const duplicateIds = new Set<string>();
  for (const group of report?.duplicate_groups ?? []) {
    for (const node of group) duplicateIds.add(`${node.kind}:${node.id}`);
  }
  return { orphanIds, staleIds, hubIds, duplicateIds };
}

export function healthScoreColor(score: number): string {
  if (score < 40) return "#ef4444";
  if (score <= 70) return "#f59e0b";
  return "#22c55e";
}
