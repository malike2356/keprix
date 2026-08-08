import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type CodingSession = {
  id: string;
  workspace_id?: string;
  objective?: string;
  status?: string;
  turn?: number;
  provider?: string;
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
}

function qs(params: Record<string, string | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value == null || value === "") continue;
    search.set(key, value);
  }
  const raw = search.toString();
  return raw ? `?${raw}` : "";
}

export async function fetchCodeAgentSessions(status?: string) {
  return parseJson<{ sessions: CodingSession[] }>(
    await ceApi(`/api/code-agent/sessions${qs({ status })}`),
    "Failed to load code-agent sessions",
  );
}

export async function fetchCodeAgentSession(id: string) {
  return parseJson<{ session: CodingSession }>(
    await ceApi(`/api/code-agent/sessions/${encodeURIComponent(id)}`),
    "Failed to load session",
  );
}

export async function fetchCodeAgentTrace(id: string) {
  return parseJson<{ events: Record<string, unknown>[] }>(
    await ceApi(`/api/code-agent/sessions/${encodeURIComponent(id)}/trace`),
    "Failed to load trace",
  );
}

export async function pauseCodeAgentSession(id: string) {
  return parseJson<{ session: CodingSession }>(
    await ceApi(`/api/code-agent/sessions/${encodeURIComponent(id)}/pause`, { method: "POST" }),
    "Failed to pause",
  );
}

export async function resumeCodeAgentSession(id: string) {
  return parseJson<{ session: CodingSession }>(
    await ceApi(`/api/code-agent/sessions/${encodeURIComponent(id)}/resume`, { method: "POST" }),
    "Failed to resume",
  );
}
