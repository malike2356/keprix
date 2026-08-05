import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type AudioStatus = {
  stt_enabled: boolean;
  provider: string | null;
  max_recording_seconds: number;
  transcribe_path?: string;
};

export type VoiceProviderCatalogItem = {
  id: string;
  label: string;
  badge?: string;
  description?: string;
  env_key?: string | null;
  needs_key?: boolean;
  has_api_key?: boolean;
  is_active?: boolean;
  key_url?: string | null;
  keyUrl?: string | null;
};

export type VoiceSettings = {
  enabled: boolean;
  provider: string | null;
  configured_provider?: string;
  configuredProvider?: string;
  max_recording_seconds: number;
  maxRecordingSeconds?: number;
  transcribe_path?: string;
  local_model?: string;
  localModel?: string;
  local_language?: string;
  localLanguage?: string;
  openai_model?: string;
  openaiModel?: string;
  mistral_model?: string;
  mistralModel?: string;
  elevenlabs_model?: string;
  elevenlabsModel?: string;
  groq_model?: string;
  groqModel?: string;
  gemini_model?: string;
  geminiModel?: string;
  auto_tts?: boolean;
  autoTts?: boolean;
  beep_enabled?: boolean;
  beepEnabled?: boolean;
  catalog: VoiceProviderCatalogItem[];
  options?: {
    local_models?: string[];
    openai_models?: string[];
    mistral_models?: string[];
    elevenlabs_models?: string[];
    groq_models?: string[];
    gemini_models?: string[];
    providers?: string[];
  };
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

export async function fetchVoiceSettings(): Promise<VoiceSettings> {
  const response = await ceApi("/api/audio/settings");
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Failed to load voice settings"));
  }
  return response.json() as Promise<VoiceSettings>;
}

export async function saveVoiceSettings(body: Record<string, unknown>): Promise<VoiceSettings> {
  const response = await ceApi("/api/audio/settings", {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Failed to save voice settings"));
  }
  return response.json() as Promise<VoiceSettings>;
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
