import { ceApi } from "@/lib/ce-api";
import { normalizeBuiltAppManifest } from "@/lib/built-app-manifest";
import type { BuiltAppManifest } from "@/components/built-app/types";

export type BuiltAppSummary = {
  id: string;
  label: string;
  description?: string | null;
  entry: string;
  icon?: string | null;
  version?: string | null;
};

export async function fetchBuiltApps(): Promise<BuiltAppSummary[]> {
  const response = await ceApi("/api/built-apps");
  if (!response.ok) {
    throw new Error("Failed to load built apps");
  }
  const payload = (await response.json()) as { apps: BuiltAppSummary[] };
  return payload.apps;
}

export async function fetchBuiltAppManifest(id: string): Promise<BuiltAppManifest> {
  const response = await ceApi(`/api/built-apps/${encodeURIComponent(id)}`);
  if (!response.ok) {
    throw new Error("Failed to load built app manifest");
  }
  const payload = (await response.json()) as { app: unknown };
  return normalizeBuiltAppManifest(payload.app);
}
