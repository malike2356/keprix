import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type ConnectorEntry = {
  id: string;
  label: string;
  category: string;
  description: string;
  icon: string;
  auth_pattern: string;
  mcp_server_id?: string | null;
  hub_pack_id?: string | null;
  sidecar_id?: string | null;
  scout_audit_class: string;
  docs_url: string;
  sample_playbook_node: Record<string, unknown>;
  featured: boolean;
  tags: string[];
  install_hint: string;
};

export type ConnectorInstallStatus = {
  installed: boolean;
  enabled?: boolean;
  reason?: string;
};

export type ConnectorCatalogItem = {
  connector: ConnectorEntry;
  install_status: ConnectorInstallStatus;
};

export type ConnectorCategory = {
  id: string;
  label: string;
  count: number;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return payload as T;
}

export async function fetchIntegrationCatalog(params?: {
  category?: string;
  featured?: boolean;
  q?: string;
  installed?: boolean;
}): Promise<ConnectorCatalogItem[]> {
  const search = new URLSearchParams();
  if (params?.category && params.category !== "all") search.set("category", params.category);
  if (typeof params?.featured === "boolean") search.set("featured", String(params.featured));
  if (params?.q) search.set("q", params.q);
  if (typeof params?.installed === "boolean") search.set("installed", String(params.installed));
  const suffix = search.toString() ? `?${search}` : "";
  const data = await parseJson<{ connectors: ConnectorCatalogItem[] }>(
    await ceApi(`/api/integrations/catalog${suffix}`),
    "Failed to load integrations",
  );
  return data.connectors || [];
}

export async function fetchIntegration(id: string): Promise<ConnectorCatalogItem> {
  return parseJson(
    await ceApi(`/api/integrations/catalog/${encodeURIComponent(id)}`),
    "Failed to load integration",
  );
}

export async function installIntegration(id: string): Promise<{
  ok: boolean;
  status: string;
  next_url?: string;
}> {
  return parseJson(
    await ceApi(`/api/integrations/catalog/${encodeURIComponent(id)}/install`, {
      method: "POST",
      body: JSON.stringify({ confirm: true }),
    }),
    "Failed to install integration",
  );
}

export async function fetchIntegrationCategories(): Promise<ConnectorCategory[]> {
  const data = await parseJson<{ categories: ConnectorCategory[] }>(
    await ceApi("/api/integrations/categories"),
    "Failed to load integration categories",
  );
  return data.categories || [];
}
