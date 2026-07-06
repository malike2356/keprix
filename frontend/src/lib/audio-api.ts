import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type AudioStatus = {
  stt_enabled: boolean;
  provider: string | null;
  max_recording_seconds: number;
  transcribe_path?: string;
};

export type TranscribeResult = {
  ok: boolean;
  transcript: string;
  provider?: string;
};

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
        return;
      }
      reject(new Error("Failed to encode audio"));
    };
    reader.onerror = () => reject(new Error("Failed to encode audio"));
    reader.readAsDataURL(blob);
  });
}

export async function fetchAudioStatus(): Promise<AudioStatus> {
  const response = await ceApi("/api/audio/status");
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Failed to load audio status"));
  }
  return response.json() as Promise<AudioStatus>;
}

export async function transcribeAudioBlob(blob: Blob): Promise<TranscribeResult> {
  const dataUrl = await blobToDataUrl(blob);
  const response = await ceApi("/api/audio/transcribe", {
    method: "POST",
    body: JSON.stringify({
      data_url: dataUrl,
      mime_type: blob.type || "audio/webm",
    }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Transcription failed"));
  }
  return response.json() as Promise<TranscribeResult>;
}
