import type { Node, XYPosition } from "@xyflow/react";
import type { BrainFlowNodeData } from "@/types/brain-graph";
import type { LayoutPositions } from "@/lib/brain/layout-types";

function nearlyEqual(left: XYPosition, right: XYPosition, epsilon = 0.5): boolean {
  return Math.abs(left.x - right.x) < epsilon && Math.abs(left.y - right.y) < epsilon;
}

export function animateLayout(
  currentNodes: Node<BrainFlowNodeData>[],
  targetPositions: LayoutPositions,
  setNodes: (nodes: Node<BrainFlowNodeData>[]) => void,
  duration = 300,
): Promise<void> {
  const movers = currentNodes
    .map((node) => {
      const target = targetPositions[node.id];
      if (!target || nearlyEqual(node.position, target)) return null;
      return {
        id: node.id,
        from: node.position,
        to: target,
      };
    })
    .filter((entry): entry is { id: string; from: XYPosition; to: XYPosition } => entry !== null);

  if (movers.length === 0) {
    const snapped = currentNodes.map((node) => ({
      ...node,
      position: targetPositions[node.id] ?? node.position,
    }));
    setNodes(snapped);
    return Promise.resolve();
  }

  const start = performance.now();

  return new Promise((resolve) => {
    const step = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - progress) ** 3;
      const byId = new Map(movers.map((mover) => [mover.id, mover]));

      const nextNodes = currentNodes.map((node) => {
        const mover = byId.get(node.id);
        if (!mover) {
          return {
            ...node,
            position: targetPositions[node.id] ?? node.position,
          };
        }
        return {
          ...node,
          position: {
            x: mover.from.x + (mover.to.x - mover.from.x) * eased,
            y: mover.from.y + (mover.to.y - mover.from.y) * eased,
          },
        };
      });

      setNodes(nextNodes);

      if (progress >= 1) {
        resolve();
        return;
      }
      requestAnimationFrame(step);
    };

    requestAnimationFrame(step);
  });
}
