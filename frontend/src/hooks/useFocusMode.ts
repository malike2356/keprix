"use client";

import * as React from "react";
import { ceApi } from "@/lib/ce-api";
import type { BrainGraphData, GraphNode } from "@/types/brain-graph";

export function useFocusMode() {
  const [focused, setFocused] = React.useState<GraphNode | null>(null);
  const [depth, setDepth] = React.useState(1);
  const [ids, setIds] = React.useState<Set<string>>(new Set());

  React.useEffect(() => {
    if (!focused) {
      setIds(new Set());
      return;
    }
    let cancelled = false;
    ceApi(`/api/brain/graph/neighbours/${encodeURIComponent(focused.kind)}/${encodeURIComponent(focused.id)}?depth=${depth}`)
      .then(async (response) => {
        if (!response.ok) throw new Error("Failed to load focus graph");
        const graph = (await response.json()) as BrainGraphData;
        if (!cancelled) setIds(new Set(graph.nodes.map((node) => `${node.kind}:${node.id}`)));
      })
      .catch(() => {
        if (!cancelled) setIds(new Set([`${focused.kind}:${focused.id}`]));
      });
    return () => {
      cancelled = true;
    };
  }, [depth, focused]);

  return {
    focused,
    focusedNodeId: focused ? `${focused.kind}:${focused.id}` : null,
    focusedIds: ids,
    depth,
    setDepth,
    focusNode: setFocused,
    clearFocus: () => setFocused(null),
  };
}
