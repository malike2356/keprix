import { KeprixClient } from "./client.js";

export type SdkManifest = {
  package: string;
  version: string;
  modules: string[];
  endpoints: Record<string, string>;
  examples: string[];
};

export async function fetchManifest(client: KeprixClient): Promise<SdkManifest> {
  return client.request<SdkManifest>("/api/sdk/typescript/manifest");
}

export async function checkLocalInstance(client: KeprixClient): Promise<{ ok: boolean; version?: string }> {
  try {
    const health = await client.request<{ status?: string; version?: string }>("/api/health");
    return { ok: health.status === "ok" || Boolean(health.version), version: health.version };
  } catch {
    return { ok: false };
  }
}

export function createLocalClient(overrides: ConstructorParameters<typeof KeprixClient>[0] = {}) {
  return new KeprixClient({
    baseUrl: overrides.baseUrl || "http://localhost:3333",
    ...overrides,
  });
}
