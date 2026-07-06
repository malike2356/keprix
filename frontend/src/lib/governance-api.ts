import { ceApi } from "@/lib/ce-api";

export type GovernancePolicy = {
  id: string;
  policy_type: string;
  policy_value: Record<string, unknown>;
  received_at?: string;
  active?: boolean;
};

export type GovernanceKillState = {
  stop_agent?: boolean;
  lock_workspace?: boolean;
  disable_tools?: boolean;
  active_directives?: Array<{ type?: string; payload?: Record<string, unknown>; received_at?: string }>;
  updated_at?: string | null;
};

export type GovernanceStatus = {
  enabled: boolean;
  connected: boolean;
  provider_endpoint?: string | null;
  instance_id?: string | null;
  enrolled_at?: string | null;
  last_heartbeat_at?: string | null;
  last_heartbeat_ok?: boolean | null;
  reporting_paused?: boolean;
  policies?: GovernancePolicy[];
  kill_state?: GovernanceKillState;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

export async function fetchGovernanceStatus(): Promise<GovernanceStatus> {
  return parseJson(await ceApi("/api/governance/status"), "governance status");
}

export async function connectGovernance(body: { provider_endpoint: string; api_key: string }) {
  return parseJson(
    await ceApi("/api/governance/connect", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "governance connect",
  );
}

export async function disconnectGovernance(acceptResponsibility: boolean) {
  return parseJson(
    await ceApi("/api/governance/disconnect", {
      method: "POST",
      body: JSON.stringify({ accept_responsibility: acceptResponsibility }),
    }),
    "governance disconnect",
  );
}

/** @deprecated Use governance-api exports */
export type ScoutStatus = GovernanceStatus;
export const fetchScoutStatus = fetchGovernanceStatus;
export const connectScout = (body: { scout_url: string; api_key: string }) =>
  connectGovernance({ provider_endpoint: body.scout_url, api_key: body.api_key });
export const disconnectScout = disconnectGovernance;
