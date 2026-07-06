import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type DeveloperApiKey = {
  id: string;
  name: string;
  key_prefix: string;
  created_at?: string;
  revoked: boolean;
  role?: string;
  usage_this_month?: number;
};

export type DeveloperWebhook = {
  id: string;
  url: string;
  events: string[];
  disabled: boolean;
  created_at?: string;
};

export type DeveloperDashboard = {
  version?: string;
  openapi_url?: string;
  docs_url?: string;
  api_keys?: DeveloperApiKey[];
  webhooks?: DeveloperWebhook[];
  usage?: { by_model?: Array<{ name: string; total: number }> };
  rate_limits?: Record<string, string>;
  models?: string[];
  enabled_tools?: string[];
  sdk_snippets?: Record<string, string>;
  recent_errors?: Array<{ path: string; status_code: number; error_message?: string }>;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return (await response.json()) as T;
}

export async function fetchDeveloperDashboard(): Promise<DeveloperDashboard> {
  return parseJson(await ceApi("/api/developer/dashboard"), "Failed to load developer dashboard");
}

export async function fetchDeveloperKeys(): Promise<DeveloperApiKey[]> {
  const payload = await parseJson<{ keys: DeveloperApiKey[] }>(
    await ceApi("/api/developer/keys"),
    "Failed to load API keys",
  );
  return payload.keys || [];
}

export async function createDeveloperKey(name: string): Promise<{ secret: string } & DeveloperApiKey> {
  return parseJson(
    await ceApi("/api/developer/keys", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
    "Failed to create API key",
  );
}

export async function revokeDeveloperKey(keyId: string): Promise<void> {
  await parseJson(await ceApi(`/api/developer/keys/${keyId}`, { method: "DELETE" }), "Failed to revoke key");
}

export async function fetchDeveloperWebhooks(): Promise<DeveloperWebhook[]> {
  const payload = await parseJson<{ webhooks: DeveloperWebhook[] }>(
    await ceApi("/api/developer/webhooks"),
    "Failed to load webhooks",
  );
  return payload.webhooks || [];
}

export async function createDeveloperWebhook(body: {
  url: string;
  events: string[];
}): Promise<{ signing_secret?: string; note?: string } & DeveloperWebhook> {
  return parseJson(
    await ceApi("/api/developer/webhooks", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to create webhook",
  );
}
