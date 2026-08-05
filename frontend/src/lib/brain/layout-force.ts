import type { Edge, Node } from "@xyflow/react";
import type { BrainFlowNodeData } from "@/types/brain-graph";
import { nodeRadius, type LayoutPositions } from "@/lib/brain/layout-types";
import { runForceSimulation, type ForceLayoutPayload } from "@/lib/brain/layout-force-core";

export function buildForcePayload(nodes: Node<BrainFlowNodeData>[], edges: Edge[]): ForceLayoutPayload {
  return {
    nodes: nodes.map((node, index) => ({
      id: node.id,
      x: node.position.x || Math.cos((index / Math.max(1, nodes.length)) * Math.PI * 2) * 120,
      y: node.position.y || Math.sin((index / Math.max(1, nodes.length)) * Math.PI * 2) * 120,
      radius: nodeRadius(node),
    })),
    edges: edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
      weight: Number((edge.data as { weight?: number } | undefined)?.weight ?? 1),
    })),
    ticks: nodes.length > 200 ? 180 : 300,
  };
}

export function applyForceLayoutSync(nodes: Node<BrainFlowNodeData>[], edges: Edge[]): LayoutPositions {
  return runForceSimulation(buildForcePayload(nodes, edges));
}

let worker: Worker | null = null;

function getForceWorker(): Worker {
  if (!worker) {
    worker = new Worker(new URL("./force-layout.worker.ts", import.meta.url), { type: "module" });
  }
  return worker;
}

export async function applyForceLayout(nodes: Node<BrainFlowNodeData>[], edges: Edge[]): Promise<LayoutPositions> {
  const payload = buildForcePayload(nodes, edges);
  if (nodes.length <= 100) {
    return runForceSimulation(payload);
  }

  return new Promise((resolve, reject) => {
    const instance = getForceWorker();
    const handleMessage = (event: MessageEvent<LayoutPositions>) => {
      instance.removeEventListener("message", handleMessage);
      instance.removeEventListener("error", handleError);
      resolve(event.data);
    };
    const handleError = (event: ErrorEvent) => {
      instance.removeEventListener("message", handleMessage);
      instance.removeEventListener("error", handleError);
      reject(event.error ?? new Error(event.message));
    };
    instance.addEventListener("message", handleMessage);
    instance.addEventListener("error", handleError);
    instance.postMessage(payload);
  });
}
