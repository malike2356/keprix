/**
 * Client for /api/security/acl (product ACL + resource grants).
 */

import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type ActorType = "agent" | "api_token" | "user" | "workspace" | "product";

export type ProductListResponse = {
  products: string[];
  base_product: string;
};

export type ProductAclDetail = {
  product_id: string;
  is_base_product: boolean;
  allowed_tools: string[];
  denied_tools: string[];
};

export type AclCheckResult = {
  product_id: string;
  tool_name: string;
  decision: string;
  allowed: boolean;
};

export type ResourceGrant = {
  actor_type: string;
  actor_id: string;
  service: string;
  kind: string;
  resource_id: string;
  actions: string[];
};

export type GrantsResponse = {
  actor_type: string;
  actor_id: string;
  grants: ResourceGrant[];
  broad_grants: Array<Record<string, unknown>>;
  note?: string;
};

export type CatalogKind = {
  kind: string;
  label?: string;
  match_mode?: string;
};

export type CatalogResponse = {
  services: Array<{
    service: string;
    label?: string;
    kinds?: CatalogKind[];
    [key: string]: unknown;
  }>;
};

export type AuditResponse = {
  count: number;
  entries: Array<Record<string, unknown>>;
};

export type ResourceCheckResult = {
  extraction: Record<string, unknown>;
  decision: Record<string, unknown>;
  allowed: boolean;
};

async function readJson<T>(response: Response, fallback: string): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return payload as T;
}

export async function listAclProducts(): Promise<ProductListResponse> {
  const response = await ceApi("/api/security/acl/products");
  return readJson(response, "Could not load ACL products");
}

export async function getProductAcl(productId: string): Promise<ProductAclDetail> {
  const response = await ceApi(`/api/security/acl/products/${encodeURIComponent(productId)}`);
  return readJson(response, "Could not load product ACL");
}

export async function checkToolAccess(productId: string, toolName: string): Promise<AclCheckResult> {
  const response = await ceApi("/api/security/acl/check", {
    method: "POST",
    body: JSON.stringify({ product_id: productId, tool_name: toolName }),
  });
  return readJson(response, "ACL check failed");
}

export async function fetchAclAudit(n = 50, productId?: string): Promise<AuditResponse> {
  const params = new URLSearchParams({ n: String(n) });
  if (productId) params.set("product_id", productId);
  const response = await ceApi(`/api/security/acl/audit?${params}`);
  return readJson(response, "Could not load ACL audit");
}

export async function fetchResourceCatalog(): Promise<CatalogResponse> {
  const response = await ceApi("/api/security/acl/resources/catalog");
  return readJson(response, "Could not load resource catalog");
}

export async function listResourceGrants(
  actorType: ActorType,
  actorId: string,
): Promise<GrantsResponse> {
  const params = new URLSearchParams({ actor_type: actorType, actor_id: actorId });
  const response = await ceApi(`/api/security/acl/resources/grants?${params}`);
  return readJson(response, "Could not load resource grants");
}

export async function upsertResourceGrant(body: {
  actor_type: ActorType;
  actor_id: string;
  service: string;
  kind: string;
  resource_id: string;
  actions: string[];
}): Promise<{ grant: ResourceGrant }> {
  const response = await ceApi("/api/security/acl/resources/grants", {
    method: "PUT",
    body: JSON.stringify(body),
  });
  return readJson(response, "Could not save resource grant");
}

export async function revokeResourceGrant(body: {
  actor_type: ActorType;
  actor_id: string;
  service: string;
  kind: string;
  resource_id: string;
}): Promise<{ revoked: boolean }> {
  const response = await ceApi("/api/security/acl/resources/grants", {
    method: "DELETE",
    body: JSON.stringify(body),
  });
  return readJson(response, "Could not revoke resource grant");
}

export async function recordBroadGrant(body: {
  actor_type: ActorType;
  actor_id: string;
  service: string;
  note?: string;
}): Promise<{ status: string; service: string }> {
  const response = await ceApi("/api/security/acl/resources/broad", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return readJson(response, "Could not record broad grant");
}

export async function checkResourceAccess(body: {
  tool_name: string;
  args: Record<string, unknown>;
  actor_type?: ActorType;
  actor_id?: string;
}): Promise<ResourceCheckResult> {
  const response = await ceApi("/api/security/acl/resources/check", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return readJson(response, "Resource ACL check failed");
}
