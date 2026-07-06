import { afterEach, describe, expect, it, vi } from "vitest";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";
import { fetchAudioStatus, transcribeAudioBlob } from "@/lib/audio-api";

vi.mock("@/lib/ce-api", () => ({
  ceApi: vi.fn(),
  parseApiErrorMessage: vi.fn((payload: unknown, fallback: string) => {
    if (payload && typeof payload === "object" && "detail" in payload) {
      const detail = (payload as { detail?: string }).detail;
      if (typeof detail === "string") {
        return detail;
      }
    }
    return fallback;
  }),
}));

const mockedCeApi = vi.mocked(ceApi);

afterEach(() => {
  vi.clearAllMocks();
});

describe("fetchAudioStatus", () => {
  it("parses status payload", async () => {
    mockedCeApi.mockResolvedValue(
      new Response(
        JSON.stringify({
          stt_enabled: true,
          provider: "local",
          max_recording_seconds: 120,
        }),
        { status: 200 },
      ),
    );

    await expect(fetchAudioStatus()).resolves.toEqual({
      stt_enabled: true,
      provider: "local",
      max_recording_seconds: 120,
    });
    expect(mockedCeApi).toHaveBeenCalledWith("/api/audio/status");
  });

  it("throws API detail on failure", async () => {
    mockedCeApi.mockResolvedValue(
      new Response(JSON.stringify({ detail: "Speech-to-text is disabled" }), { status: 403 }),
    );

    await expect(fetchAudioStatus()).rejects.toThrow("Speech-to-text is disabled");
    expect(parseApiErrorMessage).toHaveBeenCalled();
  });
});

describe("transcribeAudioBlob", () => {
  it("posts base64 audio to transcribe endpoint", async () => {
    mockedCeApi.mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true, transcript: "hello", provider: "local" }),
        { status: 200 },
      ),
    );

    const blob = new Blob(["hello"], { type: "audio/webm" });
    await expect(transcribeAudioBlob(blob)).resolves.toEqual({
      ok: true,
      transcript: "hello",
      provider: "local",
    });

    expect(mockedCeApi).toHaveBeenCalledWith(
      "/api/audio/transcribe",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"mime_type":"audio/webm"'),
      }),
    );
  });

  it("throws on transcribe failure", async () => {
    mockedCeApi.mockResolvedValue(
      new Response(JSON.stringify({ detail: "Transcription failed" }), { status: 400 }),
    );

    await expect(transcribeAudioBlob(new Blob(["x"], { type: "audio/webm" }))).rejects.toThrow(
      "Transcription failed",
    );
  });
});
