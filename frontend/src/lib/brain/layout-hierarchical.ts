import type { Node } from "@xyflow/react";
import type { BrainFlowNodeData } from "@/types/brain-graph";
import { spreadPositions, type LayoutInput, type LayoutPositions } from "@/lib/brain/layout-types";

const LAYER_HEIGHT = 140;
const NODE_WIDTH = 120;

export function applyHierarchicalLayout({ nodes, edges }: LayoutInput): LayoutPositions {
  const flowNodes = nodes as Node<BrainFlowNodeData>[];
  if (flowNodes.length === 0) return {};

  const degree = new Map<string, number>();
  for (const node of flowNodes) degree.set(node.id, 0);
  for (const edge of edges) {
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1);
  }

  const outgoing = new Map<string, string[]>();
  for (const edge of edges) {
    const list = outgoing.get(edge.source) ?? [];
    list.push(edge.target);
    outgoing.set(edge.source, list);
  }

  const sorted = [...flowNodes].sort(
    (left, right) => (degree.get(right.id) ?? 0) - (degree.get(left.id) ?? 0),
  );
  const layer = new Map<string, number>();
  const queue: string[] = [];

  for (const node of sorted) {
    layer.set(node.id, 0);
    queue.push(node.id);
  }

  // Cap depth at node count: any path longer than n must involve a cycle.
  // Use an index pointer instead of Array.shift() so each step is O(1) not O(n).
  const MAX_LAYER = flowNodes.length;
  let qi = 0;

  while (qi < queue.length) {
    const current = queue[qi++];
    const currentLayer = layer.get(current) ?? 0;
    for (const target of outgoing.get(current) ?? []) {
      const nextLayer = currentLayer + 1;
      if (nextLayer > MAX_LAYER) continue;
      const existing = layer.get(target);
      if (existing === undefined || nextLayer > existing) {
        layer.set(target, nextLayer);
        queue.push(target);
      }
    }
  }

  const maxLayer = Math.max(0, ...Array.from(layer.values()));
  for (const node of flowNodes) {
    if (!layer.has(node.id)) {
      layer.set(node.id, maxLayer + 1);
    }
  }

  const byLayer = new Map<number, Node<BrainFlowNodeData>[]>();
  for (const node of flowNodes) {
    const bucket = byLayer.get(layer.get(node.id) ?? 0) ?? [];
    bucket.push(node);
    byLayer.set(layer.get(node.id) ?? 0, bucket);
  }

  const positions: LayoutPositions = {};
  for (const [layerIndex, layerNodes] of byLayer.entries()) {
    layerNodes.sort(
      (left, right) => (degree.get(right.id) ?? 0) - (degree.get(left.id) ?? 0),
    );
    const rowWidth = Math.max(layerNodes.length * NODE_WIDTH, NODE_WIDTH);
    layerNodes.forEach((node, index) => {
      positions[node.id] = {
        x: index * NODE_WIDTH - rowWidth / 2,
        y: layerIndex * LAYER_HEIGHT,
      };
    });
  }

  return spreadPositions(flowNodes, positions);
}
