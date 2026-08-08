import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type CompanionPairingSession = {
  pairing_id: string;
  code: string;
  expires_at: string;
  qr_payload?: string;
  qr?: string;
};

export type CompanionDevice = {
  device_id: string;
  device_name?: string;
  name?: string;
  platform?: string;
  workspace_id?: string;
  last_seen_at?: string;
  paired_at?: string;
  [key: string]: unknown;
};

const DEFAULT_WORKSPACE = "default";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
}

function qs(params: Record<string, string | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value == null || value === "") continue;
    search.set(key, value);
  }
  const raw = search.toString();
  return raw ? `?${raw}` : "";
}

export async function createCompanionPairing(opts?: {
  workspaceId?: string;
  serverUrl?: string;
}) {
  return parseJson<CompanionPairingSession>(
    await ceApi(
      `/api/companion/pair${qs({
        workspace_id: opts?.workspaceId || DEFAULT_WORKSPACE,
        server_url: opts?.serverUrl,
      })}`,
      { method: "POST" },
    ),
    "Failed to create companion pairing",
  );
}

export async function fetchCompanionDevices(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ devices: CompanionDevice[] }>(
    await ceApi(`/api/companion/paired${qs({ workspace_id: workspaceId })}`),
    "Failed to load paired devices",
  );
}

export async function revokeCompanionDevice(deviceId: string) {
  return parseJson<{ removed: boolean; device_id: string }>(
    await ceApi(`/api/companion/paired/${encodeURIComponent(deviceId)}`, {
      method: "DELETE",
    }),
    "Failed to revoke companion device",
  );
}
