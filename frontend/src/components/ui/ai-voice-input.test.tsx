import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AIVoiceInput } from "@/components/ui/ai-voice-input";

function renderVoice(ui: ReactElement) {
  return render(<div className="kp-voice-root">{ui}</div>);
}

afterEach(() => {
  cleanup();
});

describe("AIVoiceInput", () => {
  it("renders mic button", () => {
    renderVoice(<AIVoiceInput onToggle={vi.fn()} recording={false} />);
    expect(screen.getByRole("button", { name: "Start voice input" })).toBeInTheDocument();
    expect(screen.getByText("Click to speak")).toBeInTheDocument();
  });

  it("click toggles listening label in controlled mode", () => {
    const onToggle = vi.fn();
    const { rerender } = renderVoice(
      <AIVoiceInput recording={false} elapsedSeconds={0} onToggle={onToggle} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Start voice input" }));
    expect(onToggle).toHaveBeenCalledTimes(1);

    rerender(
      <div className="kp-voice-root">
        <AIVoiceInput recording elapsedSeconds={3} onToggle={onToggle} />
      </div>,
    );
    expect(screen.getByText("Listening...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stop recording" })).toHaveAttribute("aria-pressed", "true");
  });

  it("disabled prevents toggle", () => {
    const onToggle = vi.fn();
    renderVoice(<AIVoiceInput recording={false} onToggle={onToggle} disabled />);
    fireEvent.click(screen.getByRole("button", { name: "Voice input unavailable" }));
    expect(onToggle).not.toHaveBeenCalled();
  });
});
