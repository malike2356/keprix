import {
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type SimulationNodeDatum,
} from "d3-force";
import type { Edge, Node, XYPosition } from "@xyflow/react";
import type { BrainFlowNodeData } from "@/types/brain-graph";
import { nodeRadius, type LayoutPositions } from "@/lib/brain/layout-types";

type ForceNode = SimulationNodeDatum & {
  id: string;
  radius: number;
  fixed: boolean;
};

function randomOffset(radius = 100): XYPosition {
  const angle = Math.random() * Math.PI * 2;
  const distance = 40 + Math.random() * radius;
  return { x: Math.cos(angle) * distance, y: Math.sin(angle) * distance };
}

export function incrementalLayout(
  existingPositions: LayoutPositions,
  newNodes: Node<BrainFlowNodeData>[],
  allEdges: Edge[],
): LayoutPositions {
  if (newNodes.length === 0) return {};

  const positions: LayoutPositions = {};
  const edgeWeight = new Map<string, number>();

  for (const edge of allEdges) {
    const weight = Number((edge.data as { weight?: number } | undefined)?.weight ?? 1);
    const forward = `${edge.source}->${edge.target}`;
    const backward = `${edge.target}->${edge.source}`;
    edgeWeight.set(forward, Math.max(edgeWeight.get(forward) ?? 0, weight));
    edgeWeight.set(backward, Math.max(edgeWeight.get(backward) ?? 0, weight));
  }

  for (const node of newNodes) {
    let bestNeighbor: string | null = null;
    let bestWeight = -1;
    for (const edge of allEdges) {
      if (edge.source === node.id && existingPositions[edge.target]) {
        const weight = edgeWeight.get(`${node.id}->${edge.target}`) ?? 0;
        if (weight > bestWeight) {
          bestWeight = weight;
          bestNeighbor = edge.target;
        }
      }
      if (edge.target === node.id && existingPositions[edge.source]) {
        const weight = edgeWeight.get(`${node.id}->${edge.source}`) ?? 0;
        if (weight > bestWeight) {
          bestWeight = weight;
          bestNeighbor = edge.source;
        }
      }
    }

    const anchor = bestNeighbor ? existingPositions[bestNeighbor] : { x: 0, y: 0 };
    const offset = randomOffset();
    positions[node.id] = { x: anchor.x + offset.x, y: anchor.y + offset.y };
  }

  const simNodes: ForceNode[] = [
    ...Object.entries(existingPositions).map(([id, position]) => ({
      id,
      x: position.x,
      y: position.y,
      radius: 32,
      fixed: true,
      fx: position.x,
      fy: position.y,
    })),
    ...newNodes.map((node) => ({
      id: node.id,
      x: positions[node.id]?.x ?? 0,
      y: positions[node.id]?.y ?? 0,
      radius: nodeRadius(node),
      fixed: false,
    })),
  ];

  const nodeById = new Map(simNodes.map((node) => [node.id, node]));
  const newIds = new Set(newNodes.map((node) => node.id));
  const links = allEdges
    .map((edge) => {
      const source = nodeById.get(edge.source);
      const target = nodeById.get(edge.target);
      if (!source || !target) return null;
      if (!newIds.has(edge.source) && !newIds.has(edge.target)) return null;
      return { source, target };
    })
    .filter((link): link is { source: ForceNode; target: ForceNode } => link !== null);

  const simulation = forceSimulation(simNodes)
    .force("link", forceLink(links).id((node) => (node as ForceNode).id).distance(80).strength(0.8))
    .force("charge", forceManyBody().strength(-40))
    .force("collision", forceCollide<ForceNode>().radius((node) => node.radius));

  simulation.stop();
  for (let index = 0; index < 60; index += 1) {
    simulation.tick();
  }

  const result: LayoutPositions = {};
  for (const node of simNodes) {
    if (newIds.has(node.id)) {
      result[node.id] = { x: node.x ?? 0, y: node.y ?? 0 };
    }
  }
  return result;
}
