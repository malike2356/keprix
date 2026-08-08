import type { Node } from "@xyflow/react";
import type { BrainFlowNodeData, BrainNodeKind } from "@/types/brain-graph";
import { spreadPositions, type LayoutInput, type LayoutPositions } from "@/lib/brain/layout-types";

const RING_BY_KIND: Record<BrainNodeKind, number> = {
  session: 0,
  memory: 1,
  document: 1,
  skill: 2,
  task: 2,
  tool: 3,
  source: 4,
  entity: 2,
};

const RING_RADIUS = [0, 220, 420, 620, 820];

export function applyRadialLayout({ nodes }: LayoutInput): LayoutPositions {
  const byRing = new Map<number, Node<BrainFlowNodeData>[]>();
  for (const node of nodes as Node<BrainFlowNodeData>[]) {
    const ring = RING_BY_KIND[node.data.kind] ?? 2;
    const bucket = byRing.get(ring) ?? [];
    bucket.push(node);
    byRing.set(ring, bucket);
  }

  const positions: LayoutPositions = {};
  for (const [ring, ringNodes] of byRing.entries()) {
    const radius = RING_RADIUS[ring] ?? 400;
    ringNodes.forEach((node, index) => {
      if (radius === 0) {
        const angle = (index / Math.max(1, ringNodes.length)) * Math.PI * 2;
        positions[node.id] = {
          x: Math.cos(angle) * 40,
          y: Math.sin(angle) * 40,
        };
        return;
      }
      const angle = (index / ringNodes.length) * Math.PI * 2;
      positions[node.id] = {
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
      };
    });
  }

  return spreadPositions(nodes as Node<BrainFlowNodeData>[], positions);
}
