import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type PermissionMode = "none" | "access" | "read" | "write";

export type DeveloperApiKey = {
  id: string;
  name: string;
  key_prefix: string;
  created_at?: string;
  revoked: boolean;
  enabled?: boolean;
  role?: string;
  usage_this_month?: number;
  monthly_limit?: number | null;
  restrict_key?: boolean;
  permissions?: Record<string, PermissionMode | string>;
  scopes?: Record<string, boolean>;
  allowed_models?: string[];
  allowed_endpoints?: string[];
  expires_at?: string | null;
  allowed_ips?: string[];
  auto_disable_if_leaked?: boolean;
  masked_key?: string;
};

export type ScopeCatalogItem = {
  id: string;
  label: string;
  modes: PermissionMode[];
  endpoints?: string[];
  path_prefixes?: string[];
  sensitive?: boolean;
  scope_flag?: string;
};

export type ScopeCatalogGroup = {
  group: string;
  items: ScopeCatalogItem[];
};

export type ScopeCatalog = {
  groups: ScopeCatalogGroup[];
  defaults: {
    restrict_key: boolean;
    permissions: Record<string, PermissionMode | string>;
    allowed_endpoints: string[];
    allowed_models: string[];
    auto_disable_if_leaked: boolean;
    expire_after_days: number | null;
  };
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
  scope_catalog?: ScopeCatalog;
  recent_errors?: Array<{ path: string; status_code: number; error_message?: string }>;
};

export type CreateApiKeyPayload = {
  name: string;
  restrict_key?: boolean;
  expire_after_days?: number | null;
  monthly_limit?: number | null;
  permissions?: Record<string, PermissionMode | string>;
  allowed_models?: string[];
  allowed_ips?: string[];
  auto_disable_if_leaked?: boolean;
  enabled?: boolean;
};

export type UpdateApiKeyPayload = {
  name?: string;
  restrict_key?: boolean;
  expire_after_days?: number | null;
  clear_expiry?: boolean;
  monthly_limit?: number | null;
  permissions?: Record<string, PermissionMode | string>;
  allowed_models?: string[];
  allowed_ips?: string[];
  auto_disable_if_leaked?: boolean;
  enabled?: boolean;
};

export type ModuleInventoryPage = {
  route: string;
  file: string;
  linked: boolean;
  dynamic: boolean;
};

export type ModuleInventoryApiModule = {
  module: string;
  file: string;
  route_count: number;
};

export type ModuleInventory = {
  navigation_count: number;
  workspace_page_count: number;
  unlinked_workspace_page_count: number;
  api_module_count: number;
  unlinked_workspace_pages: ModuleInventoryPage[];
  workspace_pages: ModuleInventoryPage[];
  api_modules: ModuleInventoryApiModule[];
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

export async function fetchModuleInventory(): Promise<ModuleInventory> {
  return parseJson(await ceApi("/api/ui/module-inventory"), "Failed to load module inventory");
}

export async function fetchDeveloperScopes(): Promise<ScopeCatalog> {
  return parseJson(await ceApi("/api/developer/scopes"), "Failed to load scope catalog");
}

export async function fetchDeveloperKeys(): Promise<DeveloperApiKey[]> {
  const payload = await parseJson<{ keys: DeveloperApiKey[] }>(
    await ceApi("/api/developer/keys"),
    "Failed to load API keys",
  );
  return payload.keys || [];
}

export async function createDeveloperKey(
  body: CreateApiKeyPayload,
): Promise<{ secret: string } & DeveloperApiKey> {
  return parseJson(
    await ceApi("/api/developer/keys", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to create API key",
  );
}

export async function updateDeveloperKey(
  keyId: string,
  body: UpdateApiKeyPayload,
): Promise<DeveloperApiKey> {
  return parseJson(
    await ceApi(`/api/developer/keys/${keyId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
    "Failed to update API key",
  );
}

export async function setDeveloperKeyEnabled(keyId: string, enabled: boolean): Promise<void> {
  await parseJson(
    await ceApi(`/api/developer/keys/${keyId}/enabled`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),
    "Failed to update key enabled state",
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
