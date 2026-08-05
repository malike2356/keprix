import { ceApi } from "@/lib/ce-api";

export type VaultItemMeta = {
  id: string;
  label: string;
  category: string;
  username?: string | null;
  url?: string | null;
  tags: string[];
  created_at?: string;
  updated_at?: string;
};

export type VaultItem = VaultItemMeta & {
  value?: string;
};

export type VaultFile = {
  path: string;
  name: string;
  is_dir: boolean;
  size: number;
  modified_at?: string | null;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(
      (payload as { detail?: string; error?: string }).detail ||
        (payload as { error?: string }).error ||
        fallback,
    );
  }
  return response.json();
}

export async function unlockVault(masterPassword: string): Promise<void> {
  await parseJson(
    await ceApi("/api/vault/unlock", {
      method: "POST",
      body: JSON.stringify({ master_password: masterPassword }),
    }),
    "Unlock failed",
  );
}

export async function lockVault(): Promise<void> {
  await parseJson(await ceApi("/api/vault/lock", { method: "POST" }), "Lock failed");
}

export async function listVaultItems(): Promise<VaultItemMeta[]> {
  const data = await parseJson<{ items: VaultItemMeta[] }>(
    await ceApi("/api/vault/items"),
    "Failed to list vault items",
  );
  return data.items;
}

export async function getVaultItem(itemId: string): Promise<VaultItem> {
  const data = await parseJson<{ item: VaultItem }>(
    await ceApi(`/api/vault/items/${itemId}`),
    "Failed to load vault item",
  );
  return data.item;
}

export async function createVaultItem(body: {
  label: string;
  category: string;
  value: string;
  username?: string;
  url?: string;
  tags?: string[];
}): Promise<VaultItemMeta> {
  const data = await parseJson<{ item: VaultItemMeta }>(
    await ceApi("/api/vault/items", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to create item",
  );
  return data.item;
}

export async function updateVaultItem(
  itemId: string,
  body: Partial<{
    label: string;
    category: string;
    value: string;
    username: string;
    url: string;
    tags: string[];
  }>,
): Promise<VaultItemMeta> {
  const data = await parseJson<{ item: VaultItemMeta }>(
    await ceApi(`/api/vault/items/${itemId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "Failed to update item",
  );
  return data.item;
}

export async function deleteVaultItem(itemId: string): Promise<void> {
  await parseJson(await ceApi(`/api/vault/items/${itemId}`, { method: "DELETE" }), "Failed to delete item");
}

export async function listVaultFiles(path = "/"): Promise<VaultFile[]> {
  const params = new URLSearchParams();
  if (path && path !== "/") {
    params.set("path", path);
  }
  const query = params.toString();
  const data = await parseJson<{ files: VaultFile[] }>(
    await ceApi(`/api/vault/files${query ? `?${query}` : ""}`),
    "Failed to list vault files",
  );
  return data.files;
}

export async function readVaultFile(path: string): Promise<string> {
  const data = await parseJson<{ content: string }>(
    await ceApi(`/api/vault/files/${encodeURIComponent(path).replace(/%2F/g, "/")}`),
    "Failed to read vault file",
  );
  return data.content;
}

export async function searchVaultFiles(query: string): Promise<VaultFile[]> {
  const params = new URLSearchParams({ query });
  const data = await parseJson<{ results: VaultFile[] }>(
    await ceApi(`/api/vault/search?${params}`),
    "Failed to search vault files",
  );
  return data.results;
}
