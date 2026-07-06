/**
 * Desktop wake word listener wrapper (Prompt 46).
 * Runs on the node with microphone access; gateway owns the trigger list.
 */

export type WakeDetectorBackend = "substring" | "whisper";

export type VoiceWakeUpdatedPayload = {
  method: "voicewake.updated";
  triggers: string[];
  routing: Record<string, unknown>;
};

export class WakeWordDetector {
  private triggers: string[];
  private backend: WakeDetectorBackend;

  constructor(triggers: string[], backend: WakeDetectorBackend = "substring") {
    this.triggers = triggers.map((value) => value.toLowerCase());
    this.backend = backend;
  }

  updateTriggers(triggers: string[]): void {
    this.triggers = triggers.map((value) => value.toLowerCase());
  }

  isTriggered(transcript: string): boolean {
    const text = transcript.toLowerCase().trim();
    return this.triggers.some((trigger) => text.includes(trigger));
  }

  matchedTrigger(transcript: string): string | null {
    const text = transcript.toLowerCase().trim();
    return this.triggers.find((trigger) => text.includes(trigger)) ?? null;
  }

  applyGatewayUpdate(payload: VoiceWakeUpdatedPayload): void {
    if (payload.method !== "voicewake.updated") return;
    this.updateTriggers(payload.triggers);
  }
}

export type LocalVoiceWakeConfig = {
  enabled: boolean;
  permissionGranted: boolean;
};

export function readLocalVoiceWakeConfig(): LocalVoiceWakeConfig {
  if (typeof window === "undefined") {
    return { enabled: false, permissionGranted: false };
  }
  const raw = window.localStorage.getItem("voice_wake");
  if (!raw) {
    return { enabled: false, permissionGranted: false };
  }
  try {
    const parsed = JSON.parse(raw) as Partial<LocalVoiceWakeConfig>;
    return {
      enabled: Boolean(parsed.enabled),
      permissionGranted: Boolean(parsed.permissionGranted),
    };
  } catch {
    return { enabled: false, permissionGranted: false };
  }
}

export function writeLocalVoiceWakeConfig(config: LocalVoiceWakeConfig): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem("voice_wake", JSON.stringify(config));
}

export function wakeDetectionAvailable(platform: string): boolean {
  return platform === "desktop" || platform === "mobile";
}
