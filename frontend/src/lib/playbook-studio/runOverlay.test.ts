import { describe, expect, it } from "vitest";
import { mapEventsToNodeStatus } from "@/lib/playbook-studio/runOverlay";
import type { PlaybookEvent } from "@/lib/playbook-api";

function event(event_type: string, node: string): PlaybookEvent {
  return {
    event_id: event_type + node,
    event_type,
    run_id: "run",
    timestamp: "2026-07-09T00:00:00Z",
    payload: { node },
  };
}

describe("mapEventsToNodeStatus", () => {
  it("maps timeline events to node statuses", () => {
    const statuses = mapEventsToNodeStatus(
      [
        event("playbook.node.started", "a"),
        event("playbook.node.completed", "a"),
        event("playbook.node.failed", "b"),
        event("playbook.approval.requested", "c"),
      ],
      ["a", "b", "c", "d"],
    );

    expect(statuses).toEqual({
      a: "completed",
      b: "failed",
      c: "waiting_approval",
      d: "pending",
    });
  });
});
