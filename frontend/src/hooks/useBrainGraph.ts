"use client";

import * as React from "react";
import { ceApi } from "@/lib/ce-api";
import type { BrainGraphData, BrainGraphFilters, GraphEdge, GraphNode } from "@/types/brain-graph";

const EMPTY_NODES: GraphNode[] = [];
const EMPTY_EDGES: GraphEdge[] = [];

function queryString(filters: BrainGraphFilters): string {
  const params = new URLSearchParams();
  if (filters.kinds?.length) params.set("kinds", filters.kinds.join(","));
  if (filters.sessionId) params.set("session_id", filters.sessionId);
  if (filters.since) params.set("since", filters.since);
  if (filters.limit) params.set("limit", String(filters.limit));
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function useBrainGraph(filters: BrainGraphFilters = {}, options?: { enabled?: boolean }) {
  const enabled = options?.enabled !== false;
  const [data, setData] = React.useState<BrainGraphData | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const key = JSON.stringify(filters);

  const refetch = React.useCallback(async () => {
    setError(null);
    const response = await ceApi(`/api/brain/graph${queryString(filters)}`);
    if (!response.ok) {
      throw new Error("Failed to load brain graph");
    }
    setData((await response.json()) as BrainGraphData);
  }, [key]);

  React.useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    refetch()
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load brain graph");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void refetch().catch(() => undefined);
      }
    }, 30000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [enabled, refetch]);

  return {
    nodes: data?.nodes ?? EMPTY_NODES,
    edges: data?.edges ?? EMPTY_EDGES,
    totalNodes: data?.total_nodes ?? 0,
    totalEdges: data?.total_edges ?? 0,
    truncated: data?.truncated ?? false,
    loading,
    error,
    refetch,
  };
}
