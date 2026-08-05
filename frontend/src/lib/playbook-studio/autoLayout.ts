import dagre from "dagre";
import type { StudioCanvas, StudioNode } from "@/lib/playbook-studio/canvas-types";

const NODE_WIDTH = 220;
const NODE_HEIGHT = 92;

export function autoLayoutCanvas(canvas: StudioCanvas): StudioCanvas {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "LR", nodesep: 56, ranksep: 96 });

  canvas.nodes.forEach((node) => {
    graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });
  canvas.edges.forEach((edge) => {
    graph.setEdge(edge.source, edge.target);
  });
  dagre.layout(graph);

  const nodes: StudioNode[] = canvas.nodes.map((node) => {
    const position = graph.node(node.id);
    if (!position) return node;
    return {
      ...node,
      position: {
        x: Math.round(position.x - NODE_WIDTH / 2),
        y: Math.round(position.y - NODE_HEIGHT / 2),
      },
    };
  });
  return { ...canvas, nodes };
}
