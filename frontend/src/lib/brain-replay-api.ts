import { ceApi } from "@/lib/ce-api";
import type { BrainSessionSummary, SessionReplayData } from "@/types/brain-replay";

export async function fetchBrainSessions(): Promise<BrainSessionSummary[]> {
  const response = await ceApi("/api/brain/sessions");
  if (!response.ok) throw new Error("Failed to load brain sessions");
  const payload = (await response.json()) as { sessions: BrainSessionSummary[] };
  return payload.sessions;
}

export async function fetchSessionReplay(sessionId: string): Promise<SessionReplayData> {
  const response = await ceApi(`/api/brain/sessions/${encodeURIComponent(sessionId)}/replay`);
  if (!response.ok) throw new Error("Failed to load session replay");
  return (await response.json()) as SessionReplayData;
}
