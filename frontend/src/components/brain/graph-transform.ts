import type { Edge, Node, XYPosition } from "@xyflow/react";
import type { ClusterGroup } from "@/components/brain/clustering";
import type { ClusterBubbleData } from "@/components/brain/ClusterBubble";
import type { BrainFlowNodeData, GraphEdge, GraphNode } from "@/types/brain-graph";

export function nodeKey(kind: string, id: string): string {
  return `${kind}:${id}`;
}

function truncate(value: string, max = 40): string {
  return value.length <= max ? value : `${value.slice(0, max - 1)}...`;
}

function degreeMap(edges: GraphEdge[]): Map<string, number> {
  const map = new Map<string, number>();
  for (const edge of edges) {
    const source = nodeKey(edge.source_kind, edge.source_id);
    const target = nodeKey(edge.target_kind, edge.target_id);
    map.set(source, (map.get(source) ?? 0) + 1);
    map.set(target, (map.get(target) ?? 0) + 1);
  }
  return map;
}

function fallbackPosition(index: number, total: number): XYPosition {
  const radius = Math.max(260, total * 18);
  const angle = (index / Math.max(1, total)) * Math.PI * 2;
  const ring = radius * (0.35 + (index % 5) * 0.12);
  return { x: Math.cos(angle) * ring + radius, y: Math.sin(angle) * ring + radius };
}

export function apiToFlowNodes(
  apiNodes: GraphNode[],
  apiEdges: GraphEdge[],
  positions?: Record<string, XYPosition>,
): Node<BrainFlowNodeData>[] {
  const degrees = degreeMap(apiEdges);
  const maxDegree = Math.max(1, ...Array.from(degrees.values()));
  return apiNodes.map((node, index) => {
    const id = nodeKey(node.kind, node.id);
    const degree = degrees.get(id) ?? 0;
    const size = 36 + Math.round((degree / maxDegree) * 36);
    return {
      id,
      type: node.deleted ? "deleted" : node.kind,
      position: positions?.[id] ?? fallbackPosition(index, apiNodes.length),
      data: { ...node, label: truncate(node.label), degree, size },
    };
  });
}

export function clustersToFlowNodes(clusters: ClusterGroup[]): Node<ClusterBubbleData>[] {
  return clusters.map((cluster) => ({
    id: cluster.id,
    type: "cluster",
    position: { x: cluster.bounds.x, y: cluster.bounds.y },
    data: {
      label: cluster.label,
      dominantKind: cluster.dominantKind,
      width: cluster.bounds.width,
      height: cluster.bounds.height,
    },
    draggable: false,
    selectable: false,
    connectable: false,
    focusable: false,
    zIndex: -1,
  }));
}

export function apiToFlowEdges(apiEdges: GraphEdge[]): Edge[] {
  return apiEdges.map((edge) => ({
    id: edge.edge_id,
    source: nodeKey(edge.source_kind, edge.source_id),
    target: nodeKey(edge.target_kind, edge.target_id),
    type: "straight",
    // Labels stay off by default; canvas shows relation on node hover.
    label: undefined,
    animated: false,
    data: { relation: edge.relation, weight: edge.weight },
    style: {
      strokeWidth: 1.15,
      opacity: 0.5,
    },
  }));
}
