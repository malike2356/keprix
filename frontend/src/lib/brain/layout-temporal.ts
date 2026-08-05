import type { Node } from "@xyflow/react";
import type { BrainFlowNodeData, BrainNodeKind } from "@/types/brain-graph";
import { spreadPositions, type LayoutInput, type LayoutPositions } from "@/lib/brain/layout-types";

const KIND_ROW: Record<BrainNodeKind, number> = {
  session: 0,
  memory: 1,
  document: 2,
  skill: 3,
  task: 4,
  tool: 5,
  source: 6,
};

const ROW_HEIGHT = 130;
const MIN_COL_WIDTH = 140;

export function applyTemporalLayout({ nodes }: LayoutInput): LayoutPositions {
  if (nodes.length === 0) return {};

  const sorted = [...nodes].sort(
    (left, right) =>
      new Date(left.data.created_at).getTime() - new Date(right.data.created_at).getTime(),
  );
  const minTime = new Date(sorted[0].data.created_at).getTime();
  const maxTime = new Date(sorted[sorted.length - 1].data.created_at).getTime();
  const span = Math.max(1, maxTime - minTime);
  const width = Math.max(sorted.length * MIN_COL_WIDTH, 900);

  const positions: LayoutPositions = {};
  for (const node of sorted) {
    const time = new Date(node.data.created_at).getTime();
    const x = ((time - minTime) / span) * width;
    const y = KIND_ROW[node.data.kind] * ROW_HEIGHT;
    positions[node.id] = { x, y };
  }

  return spreadPositions(nodes as Node<BrainFlowNodeData>[], positions);
}
