import { describe, expect, it } from "vitest";
import { apiToFlowEdges, apiToFlowNodes } from "@/components/brain/graph-transform";
import type { GraphEdge, GraphNode } from "@/types/brain-graph";

const baseNode = {
  summary: "summary",
  created_at: "2026-07-09T10:00:00Z",
  updated_at: null,
  metadata: {},
  deleted: false,
} satisfies Omit<GraphNode, "id" | "kind" | "label">;

describe("brain graph transforms", () => {
  it("sizes nodes by degree and renders tombstones as deleted nodes", () => {
    const nodes: GraphNode[] = [
      { ...baseNode, id: "mem-1", kind: "memory", label: "Important memory item" },
      { ...baseNode, id: "sess-1", kind: "session", label: "Session", deleted: true },
      { ...baseNode, id: "tool-1", kind: "tool", label: "Tool" },
    ];
    const edges: GraphEdge[] = [
      {
        edge_id: "edge-1",
        source_kind: "memory",
        source_id: "mem-1",
        target_kind: "session",
        target_id: "sess-1",
        relation: "derived_from",
        weight: 5,
        created_at: "2026-07-09T10:00:00Z",
        metadata: {},
      },
      {
        edge_id: "edge-2",
        source_kind: "memory",
        source_id: "mem-1",
        target_kind: "tool",
        target_id: "tool-1",
        relation: "used_in",
        weight: 1,
        created_at: "2026-07-09T10:00:00Z",
        metadata: {},
      },
    ];

    const flowNodes = apiToFlowNodes(nodes, edges);
    const flowEdges = apiToFlowEdges(edges);

    expect(flowNodes.find((node) => node.id === "session:sess-1")?.type).toBe("deleted");
    expect(flowNodes.find((node) => node.id === "memory:mem-1")?.data.size).toBeGreaterThan(
      flowNodes.find((node) => node.id === "tool:tool-1")?.data.size ?? 0,
    );
    expect(flowEdges[0].type).toBe("straight");
    expect(flowEdges[0].animated).toBe(false);
    expect(Number(flowEdges[0].style?.strokeWidth)).toBe(1.15);
    expect(Number(flowEdges[1].style?.strokeWidth)).toBe(1.15);
  });
});
