import type { Edge, Node, XYPosition } from "@xyflow/react";
import type { BrainFlowNodeData } from "@/types/brain-graph";

export type LayoutMode = "force" | "temporal" | "radial" | "hierarchical";

export type LayoutPositions = Record<string, XYPosition>;

export type LayoutInput = {
  nodes: Node<BrainFlowNodeData>[];
  edges: Edge[];
};

export type LayoutFn = (input: LayoutInput) => LayoutPositions | Promise<LayoutPositions>;

export function nodeRadius(node: Node<BrainFlowNodeData>): number {
  return (node.data.size ?? 44) / 2 + 20;
}

export function spreadPositions(
  nodes: Node<BrainFlowNodeData>[],
  positions: LayoutPositions,
  minGap = 8,
): LayoutPositions {
  const placed: Array<{ id: string; x: number; y: number; r: number }> = [];
  const result: LayoutPositions = {};

  for (const node of nodes) {
    const base = positions[node.id] ?? node.position;
    let x = base.x;
    let y = base.y;
    const r = nodeRadius(node);

    for (let attempt = 0; attempt < 24; attempt += 1) {
      const collision = placed.some(
        (other) => Math.hypot(other.x - x, other.y - y) < other.r + r + minGap,
      );
      if (!collision) break;
      const angle = (attempt / 24) * Math.PI * 2;
      x = base.x + Math.cos(angle) * (r + minGap + attempt * 4);
      y = base.y + Math.sin(angle) * (r + minGap + attempt * 4);
    }

    placed.push({ id: node.id, x, y, r });
    result[node.id] = { x, y };
  }

  return result;
}
