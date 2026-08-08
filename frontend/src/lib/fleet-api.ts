import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type FleetInstance = {
  id: string;
  name: string;
  base_url: string;
  version: string;
  status: string;
  last_seen_at?: string;
  cpu_pct?: number;
  ram_pct?: number;
  disk_pct?: number;
  alerts?: number;
};

export type FleetAuditEvent = {
  at: string;
  action: string;
  payload?: Record<string, unknown>;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const err = new Error(parseApiErrorMessage(payload, fallback)) as Error & {
      status?: number;
      code?: string;
      payload?: unknown;
    };
    err.status = response.status;
    err.code = typeof (payload as { code?: string }).code === "string"
      ? (payload as { code: string }).code
      : undefined;
    err.payload = payload;
    throw err;
  }
  return response.json();
}

export async function fetchFleetInstances() {
  return parseJson<{ instances: FleetInstance[] }>(
    await ceApi("/api/fleet/instances"),
    "Failed to load fleet instances",
  );
}

export async function registerFleetInstance(body: {
  name: string;
  base_url: string;
  version?: string;
}) {
  return parseJson<{ instance: FleetInstance }>(
    await ceApi("/api/fleet/instances", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to register fleet instance",
  );
}

export async function probeFleetInstance(instanceId: string) {
  return parseJson<{ instance: FleetInstance }>(
    await ceApi(`/api/fleet/instances/${encodeURIComponent(instanceId)}/probe`, {
      method: "POST",
    }),
    "Failed to probe fleet instance",
  );
}

export async function removeFleetInstance(instanceId: string) {
  return parseJson<{ removed: boolean; instance_id: string }>(
    await ceApi(`/api/fleet/instances/${encodeURIComponent(instanceId)}`, {
      method: "DELETE",
    }),
    "Failed to remove fleet instance",
  );
}

export async function fetchFleetAudit(limit = 50) {
  return parseJson<{ events: FleetAuditEvent[] }>(
    await ceApi(`/api/fleet/audit?limit=${limit}`),
    "Failed to load fleet audit",
  );
}

export function isEnterpriseRequiredError(err: unknown): boolean {
  if (!err || typeof err !== "object") return false;
  const e = err as { status?: number; code?: string; message?: string; payload?: { code?: string } };
  if (e.code === "enterprise_required" || e.payload?.code === "enterprise_required") return true;
  if (e.status === 403 && String(e.message || "").toLowerCase().includes("enterprise")) return true;
  return false;
}
