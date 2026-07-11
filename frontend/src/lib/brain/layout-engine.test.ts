import { describe, expect, it } from "vitest";
import type { Edge, Node } from "@xyflow/react";
import { detectClusters } from "@/components/brain/clustering";
import { apiToFlowEdges, apiToFlowNodes } from "@/components/brain/graph-transform";
import { incrementalLayout } from "@/lib/brain/layout-incremental";
import { applyHierarchicalLayout } from "@/lib/brain/layout-hierarchical";
import { applyRadialLayout } from "@/lib/brain/layout-radial";
import { applyTemporalLayout } from "@/lib/brain/layout-temporal";
import type { BrainFlowNodeData, GraphEdge, GraphNode } from "@/types/brain-graph";

const baseNode = {
  summary: "summary",
  created_at: "2026-07-09T10:00:00Z",
  updated_at: null,
  metadata: {},
  deleted: false,
} satisfies Omit<GraphNode, "id" | "kind" | "label">;

function buildGraph(count: number) {
  const nodes: GraphNode[] = Array.from({ length: count }, (_, index) => ({
    ...baseNode,
    id: `node-${index}`,
    kind: index % 2 === 0 ? "memory" : "session",
    label: `topic alpha node ${index}`,
    created_at: new Date(Date.UTC(2026, 0, 10 + (index % 20))).toISOString(),
  }));
  const edges: GraphEdge[] = Array.from({ length: count - 1 }, (_, index) => ({
    edge_id: `edge-${index}`,
    source_kind: nodes[index].kind,
    source_id: nodes[index].id,
    target_kind: nodes[index + 1].kind,
    target_id: nodes[index + 1].id,
    relation: "related",
    weight: 1 + (index % 3),
    created_at: "2026-07-09T10:00:00Z",
    metadata: {},
  }));
  return { nodes, edges };
}

function asLayoutInput(nodes: Node<BrainFlowNodeData>[], edges: Edge[]) {
  return { nodes, edges };
}

describe("brain layout engine", () => {
  it("places temporal layout nodes on distinct coordinates", () => {
    const { nodes, edges } = buildGraph(12);
    const flowNodes = apiToFlowNodes(nodes, edges);
    const positions = applyTemporalLayout(asLayoutInput(flowNodes, apiToFlowEdges(edges)));
    const coords = new Set(Object.values(positions).map((point) => `${point.x}:${point.y}`));
    expect(coords.size).toBe(flowNodes.length);
  });

  it("places radial and hierarchical layouts without overlap at the same coordinate", () => {
    const { nodes, edges } = buildGraph(20);
    const flowNodes = apiToFlowNodes(nodes, edges);
    const flowEdges = apiToFlowEdges(edges);
    for (const apply of [applyRadialLayout, applyHierarchicalLayout]) {
      const positions = apply(asLayoutInput(flowNodes, flowEdges));
      const coords = Object.values(positions);
      for (let left = 0; left < coords.length; left += 1) {
        for (let right = left + 1; right < coords.length; right += 1) {
          const distance = Math.hypot(coords[left].x - coords[right].x, coords[left].y - coords[right].y);
          expect(distance).toBeGreaterThan(8);
        }
      }
    }
  });

  it("detects multiple clusters for medium graphs", () => {
    const left = buildGraph(30);
    const right = buildGraph(30);
    const nodes = [...left.nodes, ...right.nodes.map((node) => ({ ...node, id: `b-${node.id}` }))];
    const edges = [
      ...left.edges,
      ...right.edges.map((edge) => ({
        ...edge,
        edge_id: `b-${edge.edge_id}`,
        source_id: `b-${edge.source_id}`,
        target_id: `b-${edge.target_id}`,
      })),
    ];
    const flowNodes = apiToFlowNodes(nodes, edges);
    const flowEdges = apiToFlowEdges(edges);
    const positions = applyHierarchicalLayout(asLayoutInput(flowNodes, flowEdges));
    const clusters = detectClusters(flowNodes, flowEdges, positions);
    expect(clusters.length).toBeGreaterThanOrEqual(2);
  });

  it("terminates hierarchical layout on cyclic graphs", () => {
    // A->B->C->A is a 3-cycle; the BFS would loop forever without the depth cap.
    const cycleNodes: Node<BrainFlowNodeData>[] = ["A", "B", "C"].map((id) => ({
      id,
      position: { x: 0, y: 0 },
      data: { id, label: id, kind: "memory", size: 44 } as BrainFlowNodeData,
      type: "brain",
    }));
    const cycleEdges: Edge[] = [
      { id: "AB", source: "A", target: "B" },
      { id: "BC", source: "B", target: "C" },
      { id: "CA", source: "C", target: "A" },
    ];
    const positions = applyHierarchicalLayout({ nodes: cycleNodes, edges: cycleEdges });
    expect(Object.keys(positions)).toHaveLength(3);
  });

  it("places incremental nodes near an existing neighbour", () => {
    const { nodes, edges } = buildGraph(3);
    const flowNodes = apiToFlowNodes(nodes, edges);
    const flowEdges = apiToFlowEdges(edges);
    const existing = {
      [flowNodes[0].id]: { x: 100, y: 100 },
      [flowNodes[1].id]: { x: 200, y: 120 },
    };
    const added = [flowNodes[2]];
    const next = incrementalLayout(existing, added, flowEdges);
    const anchor = existing[flowNodes[1].id];
    const placed = next[flowNodes[2].id];
    expect(placed).toBeDefined();
    expect(Math.hypot(placed.x - anchor.x, placed.y - anchor.y)).toBeLessThan(180);
  });
});
