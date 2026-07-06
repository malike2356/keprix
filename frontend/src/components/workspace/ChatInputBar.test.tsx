import { ThemeProvider } from "@mui/material/styles";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ChatInputBar from "@/components/workspace/ChatInputBar";
import type { UseWebVoiceRecorderOptions } from "@/hooks/useWebVoiceRecorder";
import { keprixTheme } from "@/theme/keprix-theme";

const mockToggle = vi.fn();
const mockCancel = vi.fn();
let hookOptions: UseWebVoiceRecorderOptions | undefined;
let mockSttAvailable = true;
let mockStatus: "idle" | "recording" | "transcribing" = "idle";

vi.mock("@/hooks/useWebVoiceRecorder", () => ({
  useWebVoiceRecorder: (options: UseWebVoiceRecorderOptions) => {
    hookOptions = options;
    return {
      toggle: mockToggle,
      cancel: mockCancel,
      status: mockStatus,
      elapsedSeconds: 0,
      level: 0,
      sttAvailable: mockSttAvailable,
      micError: null,
    };
  },
}));

vi.mock("@/lib/workspace-api", () => ({
  uploadChatFile: vi.fn(),
}));

function renderBar(ui: ReactElement) {
  return render(<ThemeProvider theme={keprixTheme}>{ui}</ThemeProvider>);
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  hookOptions = undefined;
  mockSttAvailable = true;
  mockStatus = "idle";
});

describe("ChatInputBar voice integration", () => {
  it("renders mic button when stt is available", () => {
    renderBar(<ChatInputBar onSend={vi.fn()} onStop={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Start voice input" })).toBeInTheDocument();
  });

  it("disables mic when streaming", () => {
    renderBar(<ChatInputBar onSend={vi.fn()} onStop={vi.fn()} isStreaming />);
    expect(hookOptions?.enabled).toBe(false);
    expect(screen.getByRole("button", { name: "Voice input unavailable" })).toBeDisabled();
  });

  it("appends transcript to the composer value", () => {
    renderBar(<ChatInputBar onSend={vi.fn()} onStop={vi.fn()} />);
    const input = screen.getByPlaceholderText("Message your agent...");

    fireEvent.change(input, { target: { value: "existing" } });
    act(() => {
      hookOptions?.onTranscript("hello from voice");
    });

    expect(input).toHaveValue("existing hello from voice");
  });

  it("send still works after voice fill", async () => {
    const onSend = vi.fn();
    renderBar(<ChatInputBar onSend={onSend} onStop={vi.fn()} />);

    act(() => {
      hookOptions?.onTranscript("dictated message");
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(onSend).toHaveBeenCalledWith("dictated message", []);
  });
});
