import { ceApi } from "@/lib/ce-api";

export type PackGateConfig = {
  workspace_id: string;
  enabled: boolean;
  approver_user_id: string | null;
  approver_email: string | null;
  notify_on_install: boolean;
  require_changelog: boolean;
};

export type PackGateRecord = {
  id: string;
  workspace_id: string;
  pack_id: string;
  from_version: string | null;
  to_version: string;
  changelog_text: string | null;
  status: string;
  signed_off_by_user_id: string | null;
  signed_off_at: string | null;
  sign_off_note: string | null;
  requested_at: string;
  requested_by_user_id: string | null;
  sign_off_url: string | null;
};

export type AdminUser = {
  id: string;
  username: string;
  email: string | null;
  role: string;
};

export async function fetchPackGateConfig(): Promise<PackGateConfig> {
  const response = await ceApi("/api/pack-gate/config");
  if (!response.ok) throw new Error("Failed to load pack gate config");
  return response.json();
}

export async function savePackGateConfig(body: Partial<PackGateConfig>): Promise<PackGateConfig> {
  const response = await ceApi("/api/pack-gate/config", {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { detail?: string }).detail || "Failed to save pack gate config");
  }
  return response.json();
}

export async function fetchPackGateRecords(params?: {
  status?: string;
  pack_id?: string;
}): Promise<{ records: PackGateRecord[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.pack_id) query.set("pack_id", params.pack_id);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const response = await ceApi(`/api/pack-gate/records${suffix}`);
  if (!response.ok) throw new Error("Failed to load pack gate records");
  return response.json();
}

export async function fetchPackGateRecord(recordId: string): Promise<PackGateRecord> {
  const response = await ceApi(`/api/pack-gate/records/${recordId}`);
  if (!response.ok) throw new Error("Failed to load gate record");
  return response.json();
}

export async function approvePackGateRecord(recordId: string, note?: string): Promise<PackGateRecord> {
  const response = await ceApi(`/api/pack-gate/records/${recordId}/approve`, {
    method: "POST",
    body: JSON.stringify({ note: note || null }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { detail?: string }).detail || "Approve failed");
  }
  return response.json();
}

export async function rejectPackGateRecord(recordId: string, note: string): Promise<PackGateRecord> {
  const response = await ceApi(`/api/pack-gate/records/${recordId}/reject`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { detail?: string }).detail || "Reject failed");
  }
  return response.json();
}

export async function fetchAdminUsers(): Promise<AdminUser[]> {
  const response = await ceApi("/api/admin/users");
  if (!response.ok) throw new Error("Failed to load users");
  const payload = await response.json();
  return payload.users ?? [];
}
