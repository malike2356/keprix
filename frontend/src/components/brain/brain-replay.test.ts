import { describe, expect, it } from "vitest";
import { buildContributionPath } from "@/components/brain/BrainPathHighlight";
import type { Edge } from "@xyflow/react";

const edges: Edge[] = [
  { id: "e1", source: "session:s1", target: "memory:m1" },
  { id: "e2", source: "memory:m1", target: "document:d1" },
];

describe("brain replay helpers", () => {
  it("finds contribution path from session to active node", () => {
    const path = buildContributionPath(edges, "session:s1", "document:d1");
    expect(path).toEqual(["e1", "e2"]);
  });
});
