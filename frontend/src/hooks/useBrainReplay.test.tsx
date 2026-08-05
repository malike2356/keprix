import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useBrainReplay } from "@/hooks/useBrainReplay";
import type { SessionReplayData } from "@/types/brain-replay";

function InlineReplayDataProbe() {
  const data: SessionReplayData = {
    session_id: "session-1",
    session_title: "Replay",
    session_date: "2026-07-10T00:00:00Z",
    messages: [
      {
        index: 0,
        role: "user",
        content: "hello",
        timestamp: "2026-07-10T00:00:00Z",
        activations_before: ["memory:m1"],
        activations_during: [],
      },
    ],
    activations: [],
    activation_count: 1,
    has_brain_activity: true,
  };
  const replay = useBrainReplay(data);
  return <div data-testid="active-count">{replay.activeNodeIds.size}</div>;
}

describe("useBrainReplay", () => {
  it("settles when replay arrays are recreated during render", async () => {
    render(<InlineReplayDataProbe />);

    await waitFor(() => expect(screen.getByTestId("active-count")).toHaveTextContent("1"));
  });
});
