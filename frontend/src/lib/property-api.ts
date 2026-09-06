import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type PropertyApiResult = {
  available: boolean;
  data: Record<string, unknown>;
};

function query(workspaceId: string): string {
  return `?workspace_id=${encodeURIComponent(workspaceId)}`;
}

export async function fetchPropertySurface(
  surface: string,
  workspaceId = "default",
): Promise<PropertyApiResult> {
  const response = await ceApi(`/api/property/${surface}${query(workspaceId)}`);
  if (response.status === 404) return { available: false, data: {} };
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, `Failed to load property ${surface}`));
  }
  const data = await response.json();
  return { available: true, data: (data && typeof data === "object" ? data : {}) as Record<string, unknown> };
}

export async function postPropertySurface(
  surface: string,
  body: Record<string, unknown>,
  workspaceId = "default",
): Promise<Record<string, unknown>> {
  const response = await ceApi(`/api/property/${surface}${query(workspaceId)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, `Property action failed: ${surface}`));
  }
  const data = await response.json();
  return (data && typeof data === "object" ? data : {}) as Record<string, unknown>;
}
