import { ceApi } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

export type WakeWordRoutingConfig = {
  version: number;
  default_target: { mode: string; node_id?: string; session_id?: string };
  device_targets: Record<string, { mode: string }>;
};

export type WakeWordsPayload = {
  triggers: string[];
  routing: WakeWordRoutingConfig;
};

export type NodeWakeStatus = {
  node_id: string;
  platform: string;
  wake_enabled: boolean;
  permission_granted: boolean;
  last_seen_at: number;
  wake_detection_available: boolean;
};

export const WAKE_WORD_MAX_COUNT = 10;
export const WAKE_WORD_MAX_LENGTH = 40;

export async function fetchWakeWords() {
  return parseJson<WakeWordsPayload>(await ceApi("/api/voice/wake-words"), "wake words");
}

export async function saveWakeWords(triggers: string[]) {
  return parseJson<{ triggers: string[] }>(
    await ceApi("/api/voice/wake-words", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ triggers }),
    }),
    "wake words save",
  );
}

export async function resetWakeWords() {
  return parseJson<{ triggers: string[] }>(
    await ceApi("/api/voice/wake-words/reset", { method: "POST" }),
    "wake words reset",
  );
}

export async function saveWakeRouting(routing: WakeWordRoutingConfig) {
  return parseJson<WakeWordRoutingConfig>(
    await ceApi("/api/voice/wake-words/routing", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(routing),
    }),
    "wake routing",
  );
}

export async function fetchWakeNodes() {
  return parseJson<{ nodes: NodeWakeStatus[] }>(
    await ceApi("/api/voice/wake-words/nodes"),
    "wake nodes",
  );
}

export function isWebWakeUnavailable(platform: string): boolean {
  return platform === "web" || platform === "cli";
}
