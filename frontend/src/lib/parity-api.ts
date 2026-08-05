import { ceApi } from "@/lib/ce-api";

async function handle<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json() as Promise<T>;
}

export async function fetchMyTenants() {
  const response = await ceApi("/api/tenants/me");
  return handle<{ tenants: Array<Record<string, unknown>>; count: number }>(response, "Failed to load tenants");
}

export async function fetchTenantsAdmin() {
  const response = await ceApi("/api/tenants");
  return handle<{ tenants: Array<Record<string, unknown>>; count: number }>(response, "Failed to load tenants");
}

export async function createTenant(body: { slug: string; display_name: string }) {
  const response = await ceApi("/api/tenants", { method: "POST", body: JSON.stringify(body) });
  return handle<{ tenant: Record<string, unknown> }>(response, "Failed to create tenant");
}

export async function fetchLeads() {
  const response = await ceApi("/api/leads");
  return handle<{ leads: Array<Record<string, unknown>>; count: number }>(response, "Failed to load leads");
}

export async function createLead(body: { name: string; email?: string }) {
  const response = await ceApi("/api/leads", { method: "POST", body: JSON.stringify(body) });
  return handle<{ lead: Record<string, unknown> }>(response, "Failed to create lead");
}

export async function fetchScoutWardenStatus() {
  const response = await ceApi("/api/scout-warden/status");
  return handle<{ enabled: boolean }>(response, "Failed to load Scout Warden status");
}

export async function requestScoutScan(target: string) {
  const response = await ceApi("/api/scout-warden/scans", {
    method: "POST",
    body: JSON.stringify({ target, tenant_id: "local" }),
  });
  return handle<Record<string, unknown>>(response, "Failed to request scan");
}

export async function fetchDsarRequests() {
  const response = await ceApi("/api/governance/dsar/requests");
  return handle<{ requests: Array<Record<string, unknown>>; count: number }>(response, "Failed to load DSAR");
}

export async function requestDsarExport(subject_user_id: string) {
  const response = await ceApi("/api/governance/dsar/export", {
    method: "POST",
    body: JSON.stringify({ subject_user_id, fulfill_now: true }),
  });
  return handle<{ request: Record<string, unknown> }>(response, "Failed to request export");
}

export async function requestDsarDelete(subject_user_id: string, dry_run = true) {
  const response = await ceApi("/api/governance/dsar/delete", {
    method: "POST",
    body: JSON.stringify({ subject_user_id, confirm: !dry_run, dry_run }),
  });
  return handle<Record<string, unknown>>(response, "Failed to request delete");
}
