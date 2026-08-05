"use client";

import type { Edge } from "@xyflow/react";

export function buildContributionPath(
  edges: Edge[],
  sessionNodeId: string,
  targetNodeId: string,
): string[] {
  const adjacency = new Map<string, Array<{ neighbor: string; edgeId: string }>>();
  for (const edge of edges) {
    const forward = adjacency.get(edge.source) ?? [];
    forward.push({ neighbor: edge.target, edgeId: edge.id });
    adjacency.set(edge.source, forward);
    const backward = adjacency.get(edge.target) ?? [];
    backward.push({ neighbor: edge.source, edgeId: edge.id });
    adjacency.set(edge.target, backward);
  }

  const queue: string[] = [targetNodeId];
  const previous = new Map<string, { node: string; edgeId: string }>();
  const visited = new Set<string>([targetNodeId]);

  while (queue.length > 0) {
    const current = queue.shift()!;
    if (current === sessionNodeId) break;
    for (const entry of adjacency.get(current) ?? []) {
      if (visited.has(entry.neighbor)) continue;
      visited.add(entry.neighbor);
      previous.set(entry.neighbor, { node: current, edgeId: entry.edgeId });
      queue.push(entry.neighbor);
    }
  }

  if (!visited.has(sessionNodeId)) return [];

  const pathEdges: string[] = [];
  let cursor: string | undefined = sessionNodeId;
  while (cursor && cursor !== targetNodeId) {
    const next = previous.get(cursor);
    if (!next) break;
    pathEdges.push(next.edgeId);
    cursor = next.node;
  }
  return pathEdges;
}
