import type { Edge, Node, XYPosition } from "@xyflow/react";
import type { BrainFlowNodeData, BrainNodeKind } from "@/types/brain-graph";

export type ClusterGroup = {
  id: string;
  nodeIds: string[];
  label: string;
  centroid: XYPosition;
  bounds: { x: number; y: number; width: number; height: number };
  dominantKind: BrainNodeKind;
};

const STOP_WORDS = new Set([
  "a",
  "an",
  "the",
  "and",
  "or",
  "for",
  "to",
  "of",
  "in",
  "on",
  "with",
  "from",
  "by",
  "is",
  "was",
  "are",
]);

function neighborsOf(nodeId: string, edges: Edge[]): Set<string> {
  const neighbors = new Set<string>();
  for (const edge of edges) {
    if (edge.source === nodeId) neighbors.add(edge.target);
    if (edge.target === nodeId) neighbors.add(edge.source);
  }
  return neighbors;
}

function connectedComponents(nodes: Node<BrainFlowNodeData>[], edges: Edge[]): string[][] {
  const ids = nodes.map((node) => node.id);
  const visited = new Set<string>();
  const components: string[][] = [];

  for (const id of ids) {
    if (visited.has(id)) continue;
    const stack = [id];
    const component: string[] = [];
    visited.add(id);
    while (stack.length > 0) {
      const current = stack.pop()!;
      component.push(current);
      for (const neighbor of neighborsOf(current, edges)) {
        if (!visited.has(neighbor)) {
          visited.add(neighbor);
          stack.push(neighbor);
        }
      }
    }
    components.push(component);
  }

  return components;
}

function modularityGain(
  nodeId: string,
  fromCommunity: Set<string>,
  toCommunity: Set<string>,
  edges: Edge[],
  degree: Map<string, number>,
  totalWeight: number,
): number {
  if (totalWeight <= 0) return 0;
  let internalDelta = 0;
  let degreeDelta = 0;
  for (const edge of edges) {
    const weight = Number((edge.data as { weight?: number } | undefined)?.weight ?? 1);
    const touchesNode = edge.source === nodeId || edge.target === nodeId;
    if (!touchesNode) continue;
    const other = edge.source === nodeId ? edge.target : edge.source;
    const wasInternal = fromCommunity.has(other);
    const willBeInternal = toCommunity.has(other);
    if (!wasInternal && willBeInternal) internalDelta += weight;
    if (wasInternal && !willBeInternal) internalDelta -= weight;
    if (willBeInternal) degreeDelta += weight;
  }
  const nodeDegree = degree.get(nodeId) ?? 0;
  return internalDelta / totalWeight - (degreeDelta * nodeDegree) / (2 * totalWeight * totalWeight);
}

function louvainLite(nodes: Node<BrainFlowNodeData>[], edges: Edge[]): Map<string, string> {
  const communities = new Map<string, string>();
  nodes.forEach((node, index) => communities.set(node.id, `c${index}`));

  const degree = new Map<string, number>();
  let totalWeight = 0;
  for (const edge of edges) {
    const weight = Number((edge.data as { weight?: number } | undefined)?.weight ?? 1);
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + weight);
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + weight);
    totalWeight += weight;
  }

  let improved = true;
  let guard = 0;
  while (improved && guard < 12) {
    improved = false;
    guard += 1;
    for (const node of nodes) {
      const currentCommunity = communities.get(node.id)!;
      const communityMembers = (target: string) =>
        new Set(
          nodes
            .filter((entry) => communities.get(entry.id) === target)
            .map((entry) => entry.id),
        );

      const neighborCommunities = new Set<string>();
      for (const neighbor of neighborsOf(node.id, edges)) {
        neighborCommunities.add(communities.get(neighbor)!);
      }

      let bestCommunity = currentCommunity;
      let bestGain = 0;
      for (const candidate of neighborCommunities) {
        if (candidate === currentCommunity) continue;
        const gain = modularityGain(
          node.id,
          communityMembers(currentCommunity),
          communityMembers(candidate),
          edges,
          degree,
          totalWeight,
        );
        if (gain > bestGain) {
          bestGain = gain;
          bestCommunity = candidate;
        }
      }

      if (bestCommunity !== currentCommunity) {
        communities.set(node.id, bestCommunity);
        improved = true;
      }
    }
  }

  return communities;
}

function clusterLabel(nodes: Node<BrainFlowNodeData>[], nodeIds: string[]): string {
  const counts = new Map<string, number>();
  for (const nodeId of nodeIds) {
    const node = nodes.find((entry) => entry.id === nodeId);
    if (!node) continue;
    for (const token of node.data.label.toLowerCase().split(/[^a-z0-9]+/)) {
      if (!token || token.length < 3 || STOP_WORDS.has(token)) continue;
      counts.set(token, (counts.get(token) ?? 0) + 1);
    }
  }
  const ranked = Array.from(counts.entries()).sort((left, right) => right[1] - left[1]);
  return ranked[0]?.[0] ?? `cluster-${nodeIds.length}`;
}

function dominantKind(nodes: Node<BrainFlowNodeData>[], nodeIds: string[]): BrainNodeKind {
  const counts = new Map<BrainNodeKind, number>();
  for (const nodeId of nodeIds) {
    const node = nodes.find((entry) => entry.id === nodeId);
    if (!node) continue;
    counts.set(node.data.kind, (counts.get(node.data.kind) ?? 0) + 1);
  }
  const ranked = Array.from(counts.entries()).sort((left, right) => right[1] - left[1]);
  return ranked[0]?.[0] ?? "memory";
}

function clusterBounds(
  nodes: Node<BrainFlowNodeData>[],
  nodeIds: string[],
  positions: Record<string, XYPosition>,
  padding = 48,
): { centroid: XYPosition; bounds: ClusterGroup["bounds"] } {
  const points = nodeIds
    .map((nodeId) => {
      const node = nodes.find((entry) => entry.id === nodeId);
      const position = positions[nodeId];
      if (!node || !position) return null;
      const radius = (node.data.size ?? 44) / 2;
      return {
        minX: position.x - radius,
        maxX: position.x + radius,
        minY: position.y - radius,
        maxY: position.y + radius,
      };
    })
    .filter((entry): entry is { minX: number; maxX: number; minY: number; maxY: number } => entry !== null);

  if (points.length === 0) {
    return {
      centroid: { x: 0, y: 0 },
      bounds: { x: -80, y: -80, width: 160, height: 160 },
    };
  }

  const minX = Math.min(...points.map((point) => point.minX)) - padding;
  const maxX = Math.max(...points.map((point) => point.maxX)) + padding;
  const minY = Math.min(...points.map((point) => point.minY)) - padding;
  const maxY = Math.max(...points.map((point) => point.maxY)) + padding;

  return {
    centroid: { x: (minX + maxX) / 2, y: (minY + maxY) / 2 },
    bounds: { x: minX, y: minY, width: maxX - minX, height: maxY - minY },
  };
}

export function detectClusters(
  nodes: Node<BrainFlowNodeData>[],
  edges: Edge[],
  positions: Record<string, XYPosition>,
): ClusterGroup[] {
  if (nodes.length < 2) return [];

  const groups =
    nodes.length < 100
      ? connectedComponents(nodes, edges).filter((group) => group.length > 1)
      : Object.values(
          (() => {
            const map = louvainLite(nodes, edges);
            return nodes.reduce<Record<string, string[]>>((acc, node) => {
              const community = map.get(node.id) ?? node.id;
              acc[community] = acc[community] ?? [];
              acc[community].push(node.id);
              return acc;
            }, {});
          })(),
        ).filter((group) => group.length > 1);

  return groups.map((nodeIds, index) => {
    const { centroid, bounds } = clusterBounds(nodes, nodeIds, positions);
    return {
      id: `cluster-${index}`,
      nodeIds,
      label: clusterLabel(nodes, nodeIds),
      centroid,
      bounds,
      dominantKind: dominantKind(nodes, nodeIds),
    };
  });
}
