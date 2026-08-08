import { ceApi } from "@/lib/ce-api";

export type FeatureFlag = {
  id: string;
  name: string;
  description: string;
  category: string;
  default: boolean;
  runtime_value: boolean;
  overridden: boolean;
  effective_value: boolean;
  tags: string[];
};

export type FeatureFlagsPayload = {
  flags: FeatureFlag[];
  categories: string[];
  override_count: number;
};

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body?.detail === "string") return body.detail;
    if (body?.detail != null) return JSON.stringify(body.detail);
  } catch {
    try {
      const text = await res.text();
      if (text) return text;
    } catch {
      /* ignore */
    }
  }
  return fallback;
}

export async function fetchFeatureFlags(): Promise<FeatureFlagsPayload> {
  const res = await ceApi("/api/admin/feature-flags");
  if (!res.ok) throw new Error(await readError(res, "Failed to load feature flags"));
  return (await res.json()) as FeatureFlagsPayload;
}

export async function setFeatureFlag(id: string, enabled: boolean): Promise<FeatureFlag> {
  const res = await ceApi(`/api/admin/feature-flags/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error(await readError(res, `Failed to update ${id}`));
  return (await res.json()) as FeatureFlag;
}

export async function resetFeatureFlag(id: string): Promise<FeatureFlag> {
  const res = await ceApi(`/api/admin/feature-flags/${encodeURIComponent(id)}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await readError(res, `Failed to reset ${id}`));
  return (await res.json()) as FeatureFlag;
}

export async function resetAllFeatureFlags(): Promise<void> {
  const res = await ceApi("/api/admin/feature-flags/reset-all", { method: "POST" });
  if (!res.ok) throw new Error(await readError(res, "Failed to reset all feature flags"));
}
