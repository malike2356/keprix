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

export type ScoutKillStatus = {
  ok: boolean;
  active: boolean;
  scope?: string | null;
  workspace_id?: string | null;
  reason?: string | null;
  activated_by?: string | null;
  activated_at?: string | null;
  sensors?: Array<Record<string, unknown>>;
  active_kills?: Array<Record<string, unknown>>;
};

export async function fetchScoutKillStatus(workspaceId = "default"): Promise<ScoutKillStatus> {
  return parseJson(
    await ceApi(`/api/scout-ops/kill/status${qs({ workspace_id: workspaceId })}`),
    "Failed to load kill status",
  );
}

export async function activateScoutKill(input: {
  workspaceId?: string;
  scope?: string;
  reason?: string;
}) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/scout-ops/kill`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workspace_id: input.workspaceId || "default",
        scope: input.scope || "workspace",
        reason: input.reason || "Operator kill from Keprix Web UI",
      }),
    }),
    "Failed to activate kill switch",
  );
}

export async function resumeScoutKill(workspaceId = "default", scope = "workspace") {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/scout-ops/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: workspaceId, scope }),
    }),
    "Failed to resume agents",
  );
}

export async function fetchScoutSensors() {
  return parseJson<{ sensors: Array<Record<string, unknown>> }>(
    await ceApi(`/api/scout-ops/sensors`),
    "Failed to load sensors",
  );
}
