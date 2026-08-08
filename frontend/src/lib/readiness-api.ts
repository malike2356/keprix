/** Client helpers for /api/admin/readiness. */

import { ceApi } from "@/lib/ce-api";

export type ReadinessStatus = "pass" | "warn" | "fail" | "unknown";
export type ReadinessCategory = "market" | "upgrade" | "recovery" | string;

export type ReadinessCheck = {
  id: string;
  title: string;
  category: ReadinessCategory;
  status: ReadinessStatus;
  summary: string;
  fix_path?: string | null;
  evidence?: Record<string, unknown>;
  docs_path?: string | null;
};

export type ReadinessReport = {
  generated_at?: string;
  overall?: ReadinessStatus;
  market?: ReadinessStatus;
  upgrade?: ReadinessStatus;
  recovery?: ReadinessStatus;
  counts?: Partial<Record<ReadinessStatus, number>>;
  notes?: string[];
  checks: ReadinessCheck[];
};

export type RestoreEvidence = {
  created_at?: number | string;
  backup_id?: string | null;
  ok?: boolean;
  restored_files?: number;
  encrypted?: boolean;
  note?: string | null;
  detail?: Record<string, unknown>;
};

async function readJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    let detail = fallback;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export async function fetchReadinessReport(targetVersion?: string): Promise<ReadinessReport> {
  const params = new URLSearchParams();
  if (targetVersion?.trim()) params.set("target_version", targetVersion.trim());
  const qs = params.toString();
  const response = await ceApi(`/api/admin/readiness${qs ? `?${qs}` : ""}`);
  return readJson(response, "Failed to load readiness report");
}

export async function createReadinessBackup(opts?: {
  password?: string | null;
  timeoutSec?: number | null;
}): Promise<Record<string, unknown>> {
  const response = await ceApi("/api/admin/readiness/backup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      password: opts?.password ?? null,
      timeout_sec: opts?.timeoutSec ?? null,
    }),
  });
  return readJson(response, "Failed to create backup");
}

export async function fetchRestoreEvidence(limit = 20): Promise<{ evidence: RestoreEvidence[] }> {
  const response = await ceApi(`/api/admin/readiness/restore-evidence?limit=${limit}`);
  return readJson(response, "Failed to load restore evidence");
}

export async function recordRestoreEvidence(body: {
  ok?: boolean;
  backup_id?: string | null;
  restored_files?: number;
  encrypted?: boolean;
  note?: string | null;
}): Promise<{ evidence: RestoreEvidence }> {
  const response = await ceApi("/api/admin/readiness/restore-evidence", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return readJson(response, "Failed to record restore evidence");
}
