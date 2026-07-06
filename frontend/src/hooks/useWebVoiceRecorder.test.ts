import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useWebVoiceRecorder } from "@/hooks/useWebVoiceRecorder";

const micStart = vi.fn();
const micStop = vi.fn();
const micCancel = vi.fn();

vi.mock("swr", () => ({
  default: (key: string) => ({
    data:
      key === "ui-contract"
        ? { feature_flags: { voice_input: true } }
        : {
            stt_enabled: true,
            provider: "local",
            max_recording_seconds: 120,
          },
  }),
}));

vi.mock("@/hooks/useMicRecorder", () => ({
  useMicRecorder: () => ({
    recording: false,
    level: 0.4,
    start: micStart,
    stop: micStop,
    cancel: micCancel,
    error: null,
  }),
}));

const transcribeAudioBlob = vi.fn();

vi.mock("@/lib/audio-api", () => ({
  fetchAudioStatus: vi.fn(),
  transcribeAudioBlob: (...args: unknown[]) => transcribeAudioBlob(...args),
}));

afterEach(() => {
  vi.clearAllMocks();
  micStart.mockResolvedValue(undefined);
  micStop.mockResolvedValue({ audio: new Blob(["audio"], { type: "audio/webm" }) });
});

describe("useWebVoiceRecorder", () => {
  it("toggle start enters recording status", async () => {
    const { result } = renderHook(() =>
      useWebVoiceRecorder({
        onTranscript: vi.fn(),
      }),
    );

    await act(async () => {
      result.current.toggle();
    });

    expect(micStart).toHaveBeenCalledTimes(1);
    expect(result.current.status).toBe("recording");
  });

  it("stop with transcript calls onTranscript", async () => {
    const onTranscript = vi.fn();
    transcribeAudioBlob.mockResolvedValue({
      ok: true,
      transcript: "hello from voice",
      provider: "local",
    });

    const { result } = renderHook(() =>
      useWebVoiceRecorder({
        onTranscript,
      }),
    );

    await act(async () => {
      result.current.toggle();
    });

    await act(async () => {
      result.current.toggle();
    });

    await waitFor(() => {
      expect(result.current.status).toBe("idle");
    });

    expect(transcribeAudioBlob).toHaveBeenCalledTimes(1);
    expect(onTranscript).toHaveBeenCalledWith("hello from voice");
  });

  it("transcribe failure calls onError", async () => {
    const onError = vi.fn();
    transcribeAudioBlob.mockRejectedValue(new Error("Transcription failed"));

    const { result } = renderHook(() =>
      useWebVoiceRecorder({
        onTranscript: vi.fn(),
        onError,
      }),
    );

    await act(async () => {
      result.current.toggle();
    });

    await act(async () => {
      result.current.toggle();
    });

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith("Transcription failed");
    });
  });
});
