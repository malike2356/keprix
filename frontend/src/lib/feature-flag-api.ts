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

export async function fetchFeatureFlags(): Promise<FeatureFlagsPayload> {
  const res = await ceApi("/api/admin/feature-flags");
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as FeatureFlagsPayload;
}

export async function setFeatureFlag(id: string, enabled: boolean): Promise<FeatureFlag> {
  const res = await ceApi(`/api/admin/feature-flags/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as FeatureFlag;
}

export async function resetFeatureFlag(id: string): Promise<FeatureFlag> {
  const res = await ceApi(`/api/admin/feature-flags/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as FeatureFlag;
}

export async function resetAllFeatureFlags(): Promise<void> {
  const res = await ceApi("/api/admin/feature-flags/reset-all", { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
}
