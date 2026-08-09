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

export type KnowledgeSource = {
  id: string;
  title: string;
  content: string;
  type: string;
  publishState: string;
  revision: number;
  language: string;
};

export type CustomerCase = {
  id: string;
  subject: string;
  status: string;
  priority: string;
  scope: string;
  audienceSessionId: string | null;
  createdAt: string;
};

export function fetchKnowledge(personaId = "default") {
  return jsonFetch<{
    sources: KnowledgeSource[];
    attachedSourceIds: string[];
    scope: string;
    notProductSupportCorpus: boolean;
  }>(`${API}/knowledge?personaId=${encodeURIComponent(personaId)}`);
}

export function createKnowledge(body: Record<string, unknown>) {
  return jsonFetch<{ ok: boolean; source: KnowledgeSource }>(`${API}/knowledge`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function setKnowledgePublishState(sourceId: string, publishState: string) {
  return jsonFetch<{ ok: boolean; source: KnowledgeSource }>(
    `${API}/knowledge/${encodeURIComponent(sourceId)}/publish-state`,
    { method: "POST", body: JSON.stringify({ publishState }) },
  );
}

export function fetchCustomerCases(personaId = "default") {
  return jsonFetch<{
    cases: CustomerCase[];
    scope: string;
    productSupportScope: string;
    note: string;
  }>(`${API}/cases?personaId=${encodeURIComponent(personaId)}`);
}

export function fetchCustomerCase(caseId: string) {
  return jsonFetch<{
    case: CustomerCase;
    internalNotes: Array<{ id: string; body: string; visibility: string }>;
    events: Array<{ eventType: string; detail: string | null }>;
    scope: string;
  }>(`${API}/cases/${encodeURIComponent(caseId)}`);
}

export function addCaseNote(caseId: string, body: string) {
  return jsonFetch<{ ok: boolean; note: { id: string; visibility: string } }>(
    `${API}/cases/${encodeURIComponent(caseId)}/notes`,
    { method: "POST", body: JSON.stringify({ body }) },
  );
}

export function takeoverSession(sessionId: string) {
  return jsonFetch<{ ok: boolean; liveTakeover: boolean }>(
    `${API}/sessions/${encodeURIComponent(sessionId)}/takeover`,
    { method: "POST" },
  );
}

export function releaseSession(sessionId: string) {
  return jsonFetch<{ ok: boolean; status: string }>(
    `${API}/sessions/${encodeURIComponent(sessionId)}/release`,
    { method: "POST" },
  );
}

export type ZoomConnection = {
  provider: string;
  oauthConfigured: boolean;
  connected: boolean;
  accountEmail: string | null;
  scopes: string[];
  status: string;
  standalone: boolean;
  fallback?: { staticRoomUrl: boolean; icsFallback: boolean; claimsManagedZoom: boolean };
};

export function fetchZoomConnection() {
  return jsonFetch<ZoomConnection>(`${API}/integrations/zoom`);
}

export function beginZoomConnect(redirectUri: string) {
  return jsonFetch<{ ok: boolean; authorizeUrl?: string; error_code?: string }>(
    `${API}/integrations/zoom/connect`,
    { method: "POST", body: JSON.stringify({ redirectUri }) },
  );
}

export function testZoomConnection() {
  return jsonFetch<{ ok: boolean; detail?: string }>(`${API}/integrations/zoom/test`, {
    method: "POST",
  });
}

export function revokeZoomConnection() {
  return jsonFetch<{ ok: boolean; revoked: boolean }>(`${API}/integrations/zoom/revoke`, {
    method: "POST",
  });
}

export type ConciergeBooking = {
  id: string;
  guestName: string;
  guestEmail: string;
  status: string;
  startsAt: string | null;
  endsAt: string | null;
  meetingUrl: string | null;
  mesh: Record<string, unknown>;
  invitation?: Record<string, unknown> | null;
  spreadsheetRow?: Record<string, unknown>;
  oneRecord?: boolean;
};

export function fetchConciergeBookings() {
  return jsonFetch<{
    bookings: ConciergeBooking[];
    outreachBookings: Array<Record<string, unknown>>;
    spreadsheetRows: Array<Record<string, unknown>>;
    oneRecordSet: boolean;
  }>(`${API}/bookings`);
}

export function fetchBookingMesh(bookingId: string) {
  return jsonFetch<{ ok: boolean; mesh: Record<string, unknown> }>(
    `${API}/bookings/${encodeURIComponent(bookingId)}/mesh`,
  );
}

export function setBookingOutcome(bookingId: string, outcome: string, conversion?: boolean) {
  return jsonFetch<{ ok: boolean }>(`${API}/bookings/${encodeURIComponent(bookingId)}/outcome`, {
    method: "POST",
    body: JSON.stringify({ outcome, conversion }),
  });
}

export type ChannelRow = {
  key: string;
  enabled: boolean;
  connected: boolean;
  consentRequired: boolean;
  setup?: string;
};

export function fetchChannels(personaId = "default") {
  return jsonFetch<{
    channels: ChannelRow[];
    published: boolean;
    embedUrl: string | null;
    gatewaySessionPath: string;
    note: string;
  }>(`${API}/channels?personaId=${encodeURIComponent(personaId)}`);
}

export function patchChannels(personaId: string, channels: Record<string, unknown>) {
  return jsonFetch<{ ok: boolean; channels: ChannelRow[] }>(
    `${API}/channels?personaId=${encodeURIComponent(personaId)}`,
    { method: "PATCH", body: JSON.stringify({ channels }) },
  );
}

export function fetchAnalytics(personaId = "default") {
  return jsonFetch<{
    privacySafe: boolean;
    metrics: Record<string, unknown>;
    derived: Record<string, number>;
    eventCounts: Record<string, number>;
  }>(`${API}/analytics?personaId=${encodeURIComponent(personaId)}`);
}

export function fetchSessionMessages(sessionId: string) {
  return jsonFetch<{
    sessionId: string;
    messages: Array<{ id?: string; role: string; body: string }>;
    internalNotes: Array<{ id: string; body: string }>;
  }>(`${API}/sessions/${encodeURIComponent(sessionId)}/messages`);
}

export function fetchLeadsTable() {
  return jsonFetch<{ rows: Array<Record<string, unknown>>; note: string }>(`${API}/leads-table`);
}

export function fetchAudienceTools(surface = "web") {
  return jsonFetch<{
    surface: string;
    ownerPrivileges: boolean;
    allowedTools: string[];
  }>(`${API}/audience-tools?surface=${encodeURIComponent(surface)}`);
}
