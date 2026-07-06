import { ceApi } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

export type MigrationItem = {
  kind: string;
  id: string;
  title: string;
  content: string;
  memory_confidence?: number | null;
  skill_category?: string | null;
  tags?: string[];
};

export type MigrationManifest = {
  schema_version: string;
  source: { name: string; kind: string };
  summary: { item_count: number; counts_by_kind: Record<string, number>; warning_count: number };
  warnings: Array<{ message: string; severity: string }>;
  items: MigrationItem[];
};

export type MigrationResult = {
  total: number;
  imported: number;
  skipped: number;
  failed: number;
  items: Array<{ id: string; status: string; error?: string | null }>;
};

export async function parseMigration(source: string, file: File) {
  const form = new FormData();
  form.append("source", source);
  form.append("file", file);
  return parseJson<MigrationManifest>(
    await ceApi("/api/migration/parse", { method: "POST", body: form }),
    "migration parse",
  );
}

export async function validateMigration(manifest: MigrationManifest) {
  return parseJson<{ valid: boolean; errors: string[] }>(
    await ceApi("/api/migration/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ manifest }),
    }),
    "migration validate",
  );
}

export async function applyMigration(manifest: MigrationManifest, approvedItemIds: string[], workspaceId = "default") {
  return parseJson<MigrationResult>(
    await ceApi("/api/migration/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        manifest,
        approved_item_ids: approvedItemIds,
        workspace_id: workspaceId,
      }),
    }),
    "migration apply",
  );
}

export async function fetchMigrationHistory(workspaceId?: string) {
  const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
  return parseJson<{ items: Array<Record<string, unknown>>; count: number }>(
    await ceApi(`/api/migration/history${query}`),
    "migration history",
  );
}

export function defaultSelectedIds(manifest: MigrationManifest): string[] {
  return manifest.items
    .filter((item) => {
      if (item.kind === "skill") return false;
      if (item.kind === "memory" && (item.memory_confidence ?? 1) < 0.6) return false;
      return true;
    })
    .map((item) => item.id);
}
