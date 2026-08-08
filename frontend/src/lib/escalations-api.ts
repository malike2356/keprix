import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const raw = search.toString();
  return raw ? `?${raw}` : "";
}

export type EscalationItem = {
  id: string;
  workspace_id: string;
  worker_id?: string;
  status?: string;
  escalation_type?: string;
  original_input?: string;
  holding_message?: string;
  confidence_score?: number | null;
  assigned_va?: string | null;
  va_response?: string | null;
  created_at?: string;
  updated_at?: string;
};

export async function fetchEscalationQueue(
  workspaceId = "default",
  status: string | null = "pending",
): Promise<{ items: EscalationItem[]; count: number }> {
  return parseJson(
    await ceApi(
      `/api/aiva/escalations/queue${qs({ workspace_id: workspaceId, status: status ?? undefined })}`,
    ),
    "Failed to load escalations",
  );
}

export async function assignEscalation(id: string, assignedVa: string): Promise<{ escalation: EscalationItem }> {
  return parseJson(
    await ceApi(`/api/aiva/escalations/${encodeURIComponent(id)}/assign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assigned_va: assignedVa }),
    }),
    "Failed to assign escalation",
  );
}

export async function completeEscalation(
  id: string,
  vaResponse: string,
  assignedVa?: string,
): Promise<{ escalation: EscalationItem }> {
  return parseJson(
    await ceApi(`/api/aiva/escalations/${encodeURIComponent(id)}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ va_response: vaResponse, assigned_va: assignedVa }),
    }),
    "Failed to complete escalation",
  );
}
