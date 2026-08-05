import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import BrainActivationTimeline from "@/components/brain/BrainActivationTimeline";

describe("BrainActivationTimeline", () => {
  it("renders activation events with live status", () => {
    render(
      <BrainActivationTimeline
        sessionId="session-1"
        paused={false}
        onPause={() => undefined}
        onClear={() => undefined}
        events={[
          {
            type: "tool_called",
            workspace_id: "default",
            session_id: "session-1",
            node_kind: "tool",
            node_id: "web_search",
            relation: "called_in_session",
            confidence: 0.9,
            ts: "2026-07-10T10:00:00.000Z",
          },
        ]}
      />,
    );

    expect(screen.getByText("Brain Activity")).toBeInTheDocument();
    expect(screen.getByText("Live: session-1")).toBeInTheDocument();
    expect(screen.getByText("web_search")).toBeInTheDocument();
    expect(screen.getByText("called_in_session")).toBeInTheDocument();
  });
});
