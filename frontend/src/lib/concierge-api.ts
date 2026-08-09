/** Customer Concierge API client (Prompt 628). */

const API = "/api/customer-concierge";

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    credentials: "include",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (data as { detail?: unknown }).detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : detail
          ? JSON.stringify(detail)
          : `Request failed (${res.status})`,
    );
  }
  return data as T;
}

export type ConciergeProfile = {
  id: string;
  workspaceId: string;
  personaId: string;
  published: boolean;
  personaName: string | null;
  greetingMessage: string | null;
  businessName: string | null;
  businessDescription: string | null;
  knowledgeSourceIds: string[];
  channelConfig: Record<string, unknown>;
  calendarProvider: string | null;
  calendarConnected: boolean;
  conferencingProvider: string | null;
  conferencingConnected: boolean;
  businessHours: {
    timezone: string;
    windows: Array<{ dayOfWeek: number; start: string; end: string }>;
  } | null;
  escalationEmail: string | null;
  icsFallbackOk?: boolean;
};

export type Readiness = {
  ready: boolean;
  checks: Array<{ key: string; label: string; status: string }>;
  blockers: string[];
  warnings: string[];
  profile?: ConciergeProfile | null;
};

export function fetchConciergeProfile(personaId = "default") {
  return jsonFetch<{ profile: ConciergeProfile | null }>(
    `${API}/profile?personaId=${encodeURIComponent(personaId)}`,
  );
}

export function saveStep1(body: Record<string, unknown>) {
  return jsonFetch<{ ok: boolean; profile: ConciergeProfile }>(`${API}/setup/step1`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function saveStep2(body: Record<string, unknown>) {
  return jsonFetch<{ ok: boolean; profile: ConciergeProfile }>(`${API}/setup/step2`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchReadiness(personaId = "default") {
  return jsonFetch<Readiness>(`${API}/readiness?personaId=${encodeURIComponent(personaId)}`);
}

export function publishConcierge(personaId = "default") {
  return jsonFetch<{ ok: boolean; profile: ConciergeProfile; widget: { publicUrl: string; embedSnippet: string } }>(
    `${API}/publish?personaId=${encodeURIComponent(personaId)}`,
    { method: "POST" },
  );
}

export function unpublishConcierge(personaId = "default") {
  return jsonFetch<{ ok: boolean; profile: ConciergeProfile }>(
    `${API}/unpublish?personaId=${encodeURIComponent(personaId)}`,
    { method: "POST" },
  );
}

export function fetchPreview(personaId = "default") {
  return jsonFetch<{
    visitorView: {
      published: boolean;
      greeting: string | null;
      personaName: string | null;
      businessName: string | null;
      publicUrl?: string;
    };
    personaOverlay: string | null;
  }>(`${API}/preview?personaId=${encodeURIComponent(personaId)}`);
}

export function publicStatus(workspaceId: string, personaId: string) {
  return jsonFetch<{
    published: boolean;
    acceptingNewSessions: boolean;
    greeting: string | null;
    personaName: string | null;
    businessName: string | null;
  }>(`/api/customer-concierge/public/${encodeURIComponent(workspaceId)}/${encodeURIComponent(personaId)}/status`);
}

export function openPublicSession(workspaceId: string, personaId: string) {
  return jsonFetch<{
    ok: boolean;
    sessionId: string;
    greeting: string | null;
    workspaceMember: boolean;
  }>(
    `/api/customer-concierge/public/${encodeURIComponent(workspaceId)}/${encodeURIComponent(personaId)}/session`,
    { method: "POST", body: "{}" },
  );
}

export function sendPublicMessage(
  workspaceId: string,
  personaId: string,
  sessionId: string,
  text: string,
) {
  return jsonFetch<{ ok: boolean; reply: string; published: boolean }>(
    `/api/customer-concierge/public/${encodeURIComponent(workspaceId)}/${encodeURIComponent(personaId)}/session/${encodeURIComponent(sessionId)}/message`,
    { method: "POST", body: JSON.stringify({ text }) },
  );
}
