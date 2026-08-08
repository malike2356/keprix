/** Channel Shield API client */

export type ShieldProtection = {
  id: string;
  channel: string;
  label: string;
  protection_key: string;
  enabled: boolean;
  verified: boolean;
  config: Record<string, unknown>;
};

export type ShieldMessage = {
  id: string;
  channel: string;
  from: string;
  subject: string;
  text_preview: string;
  status: string;
  verdict: string | null;
  safe_summary: string | null;
  report: Record<string, unknown>;
  envelope: Record<string, unknown>;
  scout_ids: string[];
  created_at: string;
  policy_label?: string | null;
  agent_safe_content?: Record<string, unknown>;
  raw_evidence_ref?: string | null;
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "x-user-id": "local",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    let detail = text || res.statusText || `HTTP ${res.status}`;
    try {
      const parsed = JSON.parse(text) as { detail?: unknown };
      if (typeof parsed?.detail === "string" && parsed.detail.trim()) {
        detail = parsed.detail;
      } else if (parsed?.detail != null) {
        detail = JSON.stringify(parsed.detail);
      }
    } catch {
      // keep raw text
    }
    throw new Error(detail);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export function fetchProtections(channel?: string) {
  const q = channel ? `?channel=${encodeURIComponent(channel)}` : "";
  return api<ShieldProtection[]>(`/api/channel-shield/protections${q}`);
}

export function createProtection(body: {
  channel: string;
  label: string;
  protection_key: string;
  config?: Record<string, unknown>;
}) {
  return api<ShieldProtection>("/api/channel-shield/protections", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchMessages(params?: { channel?: string; status?: string }) {
  const sp = new URLSearchParams();
  if (params?.channel) sp.set("channel", params.channel);
  if (params?.status) sp.set("status", params.status);
  const q = sp.toString() ? `?${sp}` : "";
  return api<ShieldMessage[]>(`/api/channel-shield/messages${q}`);
}

export function fetchMessage(id: string) {
  return api<ShieldMessage & { events: unknown[]; attachments: unknown[] }>(
    `/api/channel-shield/messages/${id}`,
  );
}

export function fetchReport(id: string) {
  return api<Record<string, unknown>>(`/api/channel-shield/messages/${id}/report`);
}

export function releaseMessage(id: string) {
  return api<Record<string, unknown>>(`/api/channel-shield/messages/${id}/release`, {
    method: "POST",
    headers: { "x-admin": "true" },
  });
}

export function destroyMessage(id: string) {
  return api<Record<string, unknown>>(`/api/channel-shield/messages/${id}/destroy`, {
    method: "POST",
    headers: { "x-admin": "true" },
  });
}

export function fetchAdapterHealth() {
  return api<{ adapters: string[]; health: Array<Record<string, unknown>> }>(
    "/api/channel-shield/adapters",
  );
}

export function fetchSettings() {
  return api<Record<string, unknown>>("/api/channel-shield/settings");
}

export type AgentOsPanel = {
  protectedAgents: Array<Record<string, unknown>>;
  blockedTriggers: Array<Record<string, unknown>>;
  approvalRequests: Array<Record<string, unknown>>;
  memoryWritesPrevented: Array<Record<string, unknown>>;
};

export type EmployeeAction = {
  messageId: string;
  verdict: string | null;
  policyLabel: string | null;
  status: string;
  safeSummary: string | null;
  agentSafeContent: Record<string, unknown>;
  evidenceAccess: string;
  rawEvidenceRef: string | null;
  allowedActions: string[];
  approvalState: string;
  auditTrail: Array<Record<string, unknown>>;
  scoutIds: string[];
};

export function fetchAgentOsPanel() {
  return api<AgentOsPanel>("/api/channel-shield/agent/os");
}

export function fetchEmployeeAction(messageId: string) {
  return api<EmployeeAction>(`/api/channel-shield/messages/${messageId}/employee-action`);
}

export function requestApproval(body: {
  message_id: string;
  agent_id?: string;
  action?: string;
}) {
  return api<Record<string, unknown>>("/api/channel-shield/agent/approvals", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
