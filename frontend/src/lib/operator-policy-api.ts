import { ceApi } from "@/lib/ce-api";

export type OperatorPolicyKnobs = {
  dual_use_depth: string;
  package_install: string;
  browser_unknown_hosts: string;
  skill_first_mode: string;
  third_party_mcp: string;
  child_safety_block: boolean;
  malware_block: boolean;
  weapons_block: boolean;
  sandboxes_enforced: boolean;
  egress_enforced: boolean;
  scout_kill_switch: boolean;
};

export type OperatorPolicy = {
  profile: "strict" | "standard" | "permissive" | string;
  source: string;
  product_id?: string;
  workspace_id?: string;
  knobs: OperatorPolicyKnobs;
  warning?: string;
};

export type OperatorPolicyResponse = {
  ok: boolean;
  policy: OperatorPolicy;
  knob_matrix: Record<string, OperatorPolicyKnobs>;
  empty_state?: string | null;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

export async function fetchOperatorPolicy(params?: {
  product_id?: string;
  workspace_id?: string;
}): Promise<OperatorPolicyResponse> {
  const qs = new URLSearchParams();
  if (params?.product_id) qs.set("product_id", params.product_id);
  if (params?.workspace_id) qs.set("workspace_id", params.workspace_id);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return parseJson(await ceApi(`/api/admin/policy${suffix}`), "operator policy");
}

export async function setOperatorPolicy(body: {
  profile: string;
  product_id?: string;
  workspace_id?: string;
}): Promise<{ ok: boolean; policy: OperatorPolicy }> {
  return parseJson(
    await ceApi("/api/admin/policy", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "set operator policy",
  );
}
