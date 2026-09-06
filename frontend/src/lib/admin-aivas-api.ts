import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type AdminAiva = {
  workspace_id: string;
  worker_id: string;
  status: string;
  channels: string[];
  tokens: number;
  cost_usd: number;
  messages: number;
  last_activity: string | null;
};

async function json<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json() as Promise<T>;
}

export async function fetchAdminAivas(): Promise<AdminAiva[]> {
  const response = await ceApi("/api/admin/aivas");
  const data = await json<{ items: AdminAiva[] }>(response, "Failed to load workers");
  return data.items || [];
}

export async function bulkGrantAdminCredits(body: {
  batch_id: string;
  reason: string;
  grants: Array<{ user_id: string; amount: number }>;
}): Promise<void> {
  await json(await ceApi("/api/admin/credits/bulk-grant", { method: "POST", body: JSON.stringify(body) }), "Failed to grant credits");
}
