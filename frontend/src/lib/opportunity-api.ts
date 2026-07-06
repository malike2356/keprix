import { ceApi } from "@/lib/ce-api";

export type OpportunityRecord = {
  opportunity_id: string;
  workspace_id: string;
  title: string;
  niche?: string | null;
  status: string;
  current_phase?: string | null;
  updated_at?: string;
};

export type OpportunityMeta = {
  status: string;
  current_phase?: string | null;
  completed_phases?: string[];
  pending_approvals?: Array<{
    approval_id: string;
    action: string;
    reason?: string;
    status?: string;
    metadata?: Record<string, unknown>;
  }>;
  validation?: { overall_score?: number; recommendation?: string };
  growth_status?: string;
  integrations_config?: Record<string, boolean>;
  launch_plan?: Record<string, unknown>;
  assets_generated?: string[];
};

export type OpportunityDetail = {
  record: OpportunityRecord;
  meta: OpportunityMeta;
};

export async function createOpportunity(body: {
  title: string;
  niche?: string;
  goal?: string;
  market?: string;
  workspace_id?: string;
}): Promise<OpportunityRecord> {
  const response = await ceApi("/api/opportunities", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Failed to create opportunity");
  return response.json();
}

export async function listOpportunities(): Promise<{ opportunities: OpportunityRecord[] }> {
  const response = await ceApi("/api/opportunities");
  if (!response.ok) throw new Error("Failed to list opportunities");
  return response.json();
}

export async function fetchOpportunity(opportunityId: string): Promise<OpportunityDetail> {
  const response = await ceApi(`/api/opportunities/${opportunityId}`);
  if (!response.ok) throw new Error("Opportunity not found");
  return response.json();
}

export async function runOpportunityPipeline(
  opportunityId: string,
  options?: { stop_at?: string; pause_on_approval?: boolean },
): Promise<Record<string, unknown>> {
  const response = await ceApi(`/api/opportunities/${opportunityId}/run`, {
    method: "POST",
    body: JSON.stringify(options ?? {}),
  });
  if (!response.ok) throw new Error("Pipeline run failed");
  return response.json();
}

export async function runOpportunityPhase(
  opportunityId: string,
  phase: string,
): Promise<Record<string, unknown>> {
  const response = await ceApi(`/api/opportunities/${opportunityId}/phase/${phase}`, {
    method: "POST",
  });
  if (!response.ok) throw new Error(`Phase ${phase} failed`);
  return response.json();
}

export async function fetchOpportunityArtifact(
  opportunityId: string,
  filename: string,
): Promise<{ filename: string; content: string }> {
  const response = await ceApi(`/api/opportunities/${opportunityId}/artifacts/${filename}`);
  if (!response.ok) throw new Error(`Artifact ${filename} not found`);
  return response.json();
}

export async function fetchOpportunityAsset(
  opportunityId: string,
  filename: string,
): Promise<{ filename: string; content: string }> {
  const response = await ceApi(`/api/opportunities/${opportunityId}/assets/${filename}`);
  if (!response.ok) throw new Error(`Asset ${filename} not found`);
  return response.json();
}

export async function approveOpportunityAction(
  opportunityId: string,
  approvalId: string,
  approved = true,
): Promise<Record<string, unknown>> {
  const response = await ceApi(`/api/opportunities/${opportunityId}/approve`, {
    method: "POST",
    body: JSON.stringify({ approval_id: approvalId, approved }),
  });
  if (!response.ok) throw new Error("Approval failed");
  return response.json();
}

export async function pauseOpportunity(opportunityId: string): Promise<OpportunityRecord> {
  const response = await ceApi(`/api/opportunities/${opportunityId}/pause`, { method: "POST" });
  if (!response.ok) throw new Error("Pause failed");
  return response.json();
}

export async function archiveOpportunity(opportunityId: string): Promise<OpportunityRecord> {
  const response = await ceApi(`/api/opportunities/${opportunityId}/archive`, { method: "POST" });
  if (!response.ok) throw new Error("Archive failed");
  return response.json();
}

export const OPPORTUNITY_STATUSES: Record<string, string> = {
  draft: "Draft",
  researching: "Researching",
  validating: "Validating",
  assets_ready: "Assets ready",
  approval_required: "Approval required",
  launch_ready: "Launch ready",
  launched: "Launched",
  paused: "Paused",
  archived: "Archived",
};

export const PLAYBOOK_PHASES = [
  "market_demand",
  "pain_mining",
  "offer_builder",
  "icp_builder",
  "competitor_intelligence",
  "validation_score",
  "offer_doc",
  "asset_factory",
  "launch_orchestrator",
  "growth_loop",
] as const;
