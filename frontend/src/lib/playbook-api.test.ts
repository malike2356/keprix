import { describe, expect, it } from "vitest";
import {
  groupPlaybookEventsByNode,
  redactStateForDisplay,
  type PlaybookEvent,
} from "@/lib/playbook-api";

describe("groupPlaybookEventsByNode", () => {
  it("merges started and completed events into one step row", () => {
    const events: PlaybookEvent[] = [
      {
        event_id: "1",
        event_type: "playbook.node.started",
        run_id: "run-1",
        timestamp: "2026-07-06T10:00:00.000Z",
        payload: {
          node: "prepare",
          input_state: { topic: "demo" },
        },
      },
      {
        event_id: "2",
        event_type: "playbook.node.completed",
        run_id: "run-1",
        timestamp: "2026-07-06T10:00:01.000Z",
        payload: {
          node: "prepare",
          input_state: { topic: "demo" },
          output_state: { topic: "demo", prepare_output: "ready" },
          duration_ms: 42,
        },
      },
    ];

    const rows = groupPlaybookEventsByNode(events);
    expect(rows).toHaveLength(1);
    expect(rows[0].node).toBe("prepare");
    expect(rows[0].status).toBe("success");
    expect(rows[0].duration_ms).toBe(42);
    expect(rows[0].output_state).toEqual({ topic: "demo", prepare_output: "ready" });
  });

  it("marks failed nodes with error payload", () => {
    const events: PlaybookEvent[] = [
      {
        event_id: "1",
        event_type: "playbook.node.failed",
        run_id: "run-1",
        timestamp: "2026-07-06T10:00:02.000Z",
        payload: {
          node: "approve",
          input_state: { approved: false },
          error: "Human rejected",
          duration_ms: 12,
        },
      },
    ];

    const rows = groupPlaybookEventsByNode(events);
    expect(rows[0].status).toBe("failed");
    expect(rows[0].error).toBe("Human rejected");
  });
});

describe("redactStateForDisplay", () => {
  it("redacts secret-like keys", () => {
    const redacted = redactStateForDisplay({
      api_token: "abc123",
      nested: { client_secret: "hidden", count: 2 },
      note: "ok",
    });
    expect(redacted).toEqual({
      api_token: "[redacted]",
      nested: { client_secret: "[redacted]", count: 2 },
      note: "ok",
    });
  });
});
