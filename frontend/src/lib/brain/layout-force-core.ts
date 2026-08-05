import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type SimulationNodeDatum,
} from "d3-force";
import type { LayoutPositions } from "@/lib/brain/layout-types";

type ForceNode = SimulationNodeDatum & {
  id: string;
  radius: number;
};

type ForceLink = {
  source: string;
  target: string;
  weight: number;
};

export type ForceLayoutPayload = {
  nodes: Array<{ id: string; x: number; y: number; radius: number }>;
  edges: ForceLink[];
  ticks?: number;
};

export function runForceSimulation(payload: ForceLayoutPayload): LayoutPositions {
  const simNodes: ForceNode[] = payload.nodes.map((node) => ({
    id: node.id,
    x: node.x,
    y: node.y,
    radius: node.radius,
  }));
  const nodeById = new Map(simNodes.map((node) => [node.id, node]));
  const links = payload.edges
    .map((edge) => {
      const source = nodeById.get(edge.source);
      const target = nodeById.get(edge.target);
      if (!source || !target) return null;
      return { source, target, weight: edge.weight };
    })
    .filter((link): link is { source: ForceNode; target: ForceNode; weight: number } => link !== null);

  const simulation = forceSimulation(simNodes)
    .force(
      "link",
      forceLink(links)
        .id((node) => (node as ForceNode).id)
        .distance((link) => 120 - Math.min(40, Math.log((link as { weight: number }).weight + 1) * 8))
        .strength(0.5),
    )
    .force("charge", forceManyBody().strength(-300))
    .force("collision", forceCollide<ForceNode>().radius((node) => node.radius))
    .force("center", forceCenter(0, 0));

  simulation.stop();
  const ticks = payload.ticks ?? 300;
  for (let index = 0; index < ticks; index += 1) {
    simulation.tick();
  }

  const positions: LayoutPositions = {};
  for (const node of simNodes) {
    positions[node.id] = { x: node.x ?? 0, y: node.y ?? 0 };
  }
  return positions;
}
