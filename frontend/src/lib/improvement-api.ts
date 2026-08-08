import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type ImprovementProposal = {
  proposal_id: string;
  run_id?: string;
  agent_id?: string;
  category?: string;
  title?: string;
  detail?: string;
  status?: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
};

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

export async function fetchImprovementProposals(status?: string) {
  return parseJson<{ proposals: ImprovementProposal[] }>(
    await ceApi(`/api/improvement/proposals${qs({ status })}`),
    "Failed to load improvement proposals",
  );
}

export async function fetchImprovementMetrics(agentId?: string) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/improvement/metrics${qs({ agent_id: agentId })}`),
    "Failed to load improvement metrics",
  );
}

async function postAction(path: string, body: Record<string, unknown>, fallback: string) {
  return parseJson<{ proposal: ImprovementProposal }>(
    await ceApi(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    fallback,
  );
}

export async function approveImprovementProposal(proposalId: string, createEvalCase = true) {
  return postAction(
    "/api/improvement/proposals/approve",
    { proposal_id: proposalId, create_eval_case: createEvalCase },
    "Failed to approve proposal",
  );
}

export async function rejectImprovementProposal(proposalId: string) {
  return postAction("/api/improvement/proposals/reject", { proposal_id: proposalId }, "Failed to reject");
}

export async function applyImprovementProposal(proposalId: string) {
  return postAction("/api/improvement/proposals/apply", { proposal_id: proposalId }, "Failed to apply");
}

export async function deferImprovementProposal(proposalId: string) {
  return postAction("/api/improvement/proposals/defer", { proposal_id: proposalId }, "Failed to defer");
}
