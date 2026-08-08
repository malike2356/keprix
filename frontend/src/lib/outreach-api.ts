import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";
import type {
  OutreachApproval,
  OutreachBooking,
  OutreachCampaign,
  OutreachControlState,
  OutreachLead,
  OutreachList,
  OutreachOverview,
  OutreachReply,
  OutreachSequence,
} from "@/components/outreach/types";

const DEFAULT_WORKSPACE = "default";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const raw = search.toString();
  return raw ? `?${raw}` : "";
}

function workspaceParams(workspaceId = DEFAULT_WORKSPACE) {
  return { workspace_id: workspaceId };
}

export async function fetchOutreachOverview(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<OutreachOverview>(
    await ceApi(`/api/outreach/overview${qs(workspaceParams(workspaceId))}`),
    "Failed to load outreach overview",
  );
}

export async function fetchOutreachControl(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ state: OutreachControlState }>(
    await ceApi(`/api/outreach/control${qs(workspaceParams(workspaceId))}`),
    "Failed to load outreach control",
  );
}

export async function patchOutreachControl(
  action: "pause" | "resume",
  reason?: string,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ state: OutreachControlState }>(
    await ceApi(`/api/outreach/control${qs(workspaceParams(workspaceId))}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, reason }),
    }),
    "Failed to update outreach control",
  );
}

export async function fetchOutreachPipeline(workspaceId = DEFAULT_WORKSPACE, campaignId?: string) {
  return parseJson<{ stages: Record<string, number>; total: number }>(
    await ceApi(
      `/api/outreach/pipeline${qs({ ...workspaceParams(workspaceId), campaign_id: campaignId })}`,
    ),
    "Failed to load pipeline",
  );
}

export async function fetchOutreachPipelineBoard(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{
    columns: Record<string, OutreachLead[]>;
    stages: string[] | Record<string, number>;
    summary?: Record<string, number>;
  }>(
    await ceApi(`/api/outreach/pipeline/board${qs(workspaceParams(workspaceId))}`),
    "Failed to load pipeline board",
  );
}

export async function fetchOutreachLeads(
  workspaceId = DEFAULT_WORKSPACE,
  opts?: { campaignId?: string; status?: string; limit?: number },
) {
  return parseJson<{ leads: OutreachLead[]; count: number }>(
    await ceApi(
      `/api/outreach/leads${qs({
        ...workspaceParams(workspaceId),
        campaign_id: opts?.campaignId,
        status: opts?.status,
        limit: opts?.limit ?? 100,
      })}`,
    ),
    "Failed to load leads",
  );
}

export async function fetchOutreachLead(leadId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ lead: OutreachLead; deliveries?: unknown[] }>(
    await ceApi(`/api/outreach/leads/${encodeURIComponent(leadId)}${qs(workspaceParams(workspaceId))}`),
    "Failed to load lead",
  );
}

export async function createOutreachLead(
  body: {
    name: string;
    email?: string;
    company?: string;
    phone?: string;
    source?: string;
    campaign_id?: string;
    tags?: string[];
  },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ lead?: OutreachLead; leads?: OutreachLead[]; created?: number }>(
    await ceApi(`/api/outreach/leads${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to create lead",
  );
}

export async function patchOutreachLead(
  leadId: string,
  body: { status?: string; notes?: string; tags?: string[] },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ lead: OutreachLead }>(
    await ceApi(`/api/outreach/leads/${encodeURIComponent(leadId)}${qs(workspaceParams(workspaceId))}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to update lead",
  );
}

export async function importOutreachLeads(
  body: { csv_text?: string; lines?: string; leads?: Array<Record<string, unknown>>; campaign_id?: string },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ created: number | unknown[]; leads?: OutreachLead[]; duplicates?: unknown[] }>(
    await ceApi(`/api/outreach/leads/import${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to import leads",
  );
}

/** @deprecated Prefer importOutreachLeads; kept for callers that POST csv to /leads */
export async function addOutreachLeadsCsv(csvText: string, workspaceId = DEFAULT_WORKSPACE, campaignId?: string) {
  return parseJson<{ created: number; leads: OutreachLead[] }>(
    await ceApi(`/api/outreach/leads${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ csv_text: csvText, campaign_id: campaignId }),
    }),
    "Failed to import leads",
  );
}

export async function enrollOutreachLead(
  body: { lead_id: string; sequence_id: string; campaign_id?: string },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ enrollment?: Record<string, unknown> }>(
    await ceApi(`/api/outreach/enrollments${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to enroll lead",
  );
}

export async function preflightOutreachListEnroll(
  listId: string,
  body: { sequence_id: string; campaign_id?: string },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{
    audience_hash: string;
    counts: Record<string, number>;
    eligible: unknown[];
    suppressed: Array<{ lead_id: string; fix_href?: string; reason?: string }>;
    contactability_deny: Array<{ lead_id: string; fix_href?: string; reason?: string }>;
    note?: string;
    deep_links?: Record<string, string>;
  }>(
    await ceApi(
      `/api/outreach/lists/${encodeURIComponent(listId)}/enroll-preflight${qs(workspaceParams(workspaceId))}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    ),
    "Failed to run enroll preflight",
  );
}

export async function enrollOutreachList(
  listId: string,
  body: {
    sequence_id: string;
    campaign_id?: string;
    audience_hash?: string;
    force?: boolean;
    approval_id?: string;
    require_soft_wall?: boolean;
  },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{
    blocked?: boolean;
    enrolled_count?: number;
    approval?: Record<string, unknown>;
    skipped?: Record<string, number>;
    audience_hash?: string;
    error_code?: string;
  }>(
    await ceApi(`/api/outreach/lists/${encodeURIComponent(listId)}/enroll${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to enroll Soft Wall list",
  );
}

export async function fetchOutreachCampaigns(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ campaigns: OutreachCampaign[]; count: number }>(
    await ceApi(`/api/outreach/campaigns${qs(workspaceParams(workspaceId))}`),
    "Failed to load campaigns",
  );
}

export async function createOutreachCampaign(
  body: string | { name: string; objective?: string; status?: string; [key: string]: unknown },
  workspaceId = DEFAULT_WORKSPACE,
) {
  const payload = typeof body === "string" ? { name: body } : body;
  return parseJson<{ campaign: OutreachCampaign }>(
    await ceApi(`/api/outreach/campaigns${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "Failed to create campaign",
  );
}

export async function patchOutreachCampaign(
  campaignId: string,
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ campaign: OutreachCampaign }>(
    await ceApi(
      `/api/outreach/campaigns/${encodeURIComponent(campaignId)}${qs(workspaceParams(workspaceId))}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    ),
    "Failed to update campaign",
  );
}

export async function fetchOutreachSequences(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ sequences: OutreachSequence[]; count: number }>(
    await ceApi(`/api/outreach/sequences${qs(workspaceParams(workspaceId))}`),
    "Failed to load sequences",
  );
}

export async function createOutreachSequence(
  body: {
    name: string;
    steps: unknown[];
    channel_default?: string;
    stop_on_reply?: boolean;
    stop_on_booking?: boolean;
    stop_on_unsubscribe?: boolean;
    description?: string;
  },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ sequence: OutreachSequence }>(
    await ceApi(`/api/outreach/sequences${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to create sequence",
  );
}

export async function patchOutreachSequence(
  sequenceId: string,
  body: {
    name?: string;
    steps?: unknown[];
    stop_on_reply?: boolean;
    stop_on_booking?: boolean;
    stop_on_unsubscribe?: boolean;
    channel_default?: string;
    description?: string;
  },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ sequence: OutreachSequence }>(
    await ceApi(
      `/api/outreach/sequences/${encodeURIComponent(sequenceId)}${qs(workspaceParams(workspaceId))}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    ),
    "Failed to update sequence",
  );
}

export async function fetchOutreachReplies(
  workspaceId = DEFAULT_WORKSPACE,
  resolved?: 0 | 1,
) {
  return parseJson<{ replies: OutreachReply[]; reviews?: OutreachReply[]; count?: number }>(
    await ceApi(
      `/api/outreach/replies${qs({
        ...workspaceParams(workspaceId),
        resolved: resolved === undefined ? undefined : resolved,
      })}`,
    ),
    "Failed to load replies",
  );
}

export async function postOutreachInboundReply(
  body: { from_email?: string; fromEmail?: string; subject?: string; body?: string; lead_id?: string },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ reply?: OutreachReply }>(
    await ceApi(`/api/outreach/replies/inbound${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to record inbound reply",
  );
}

export async function resolveOutreachReply(
  replyId: string,
  body: { classification?: string; note?: string },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ reply?: OutreachReply }>(
    await ceApi(
      `/api/outreach/replies/${encodeURIComponent(replyId)}/resolve${qs(workspaceParams(workspaceId))}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    ),
    "Failed to resolve reply",
  );
}

export async function fetchOutreachLists(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ lists: OutreachList[]; count?: number }>(
    await ceApi(`/api/outreach/lists${qs(workspaceParams(workspaceId))}`),
    "Failed to load lists",
  );
}

export async function createOutreachList(
  body: { name: string; description?: string; lead_ids?: string[]; tags?: string[] },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ list: OutreachList }>(
    await ceApi(`/api/outreach/lists${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to create list",
  );
}

export async function patchOutreachList(
  listId: string,
  body: { name?: string; description?: string; lead_ids?: string[]; tags?: string[] },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ list: OutreachList }>(
    await ceApi(`/api/outreach/lists/${encodeURIComponent(listId)}${qs(workspaceParams(workspaceId))}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to update list",
  );
}

export async function addLeadsToOutreachList(
  listId: string,
  leadIds: string[],
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ list: OutreachList }>(
    await ceApi(
      `/api/outreach/lists/${encodeURIComponent(listId)}/leads${qs(workspaceParams(workspaceId))}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lead_ids: leadIds }),
      },
    ),
    "Failed to add leads to list",
  );
}

export async function fetchOutreachBookings(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ bookings: OutreachBooking[]; count?: number }>(
    await ceApi(`/api/outreach/bookings${qs(workspaceParams(workspaceId))}`),
    "Failed to load bookings",
  );
}

export async function createOutreachBooking(
  body: {
    lead_id: string;
    starts_at: string;
    ends_at?: string;
    status?: string;
    notes?: string;
    attendee_name?: string;
    attendee_email?: string;
  },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ booking: OutreachBooking }>(
    await ceApi(`/api/outreach/bookings${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to create booking",
  );
}

export async function updateOutreachBookingStatus(
  bookingId: string,
  status: string,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ booking: OutreachBooking }>(
    await ceApi(
      `/api/outreach/bookings/${encodeURIComponent(bookingId)}/status${qs(workspaceParams(workspaceId))}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      },
    ),
    "Failed to update booking status",
  );
}

export async function fetchOutreachApprovals(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ approvals: OutreachApproval[]; count?: number }>(
    await ceApi(`/api/outreach/approvals${qs(workspaceParams(workspaceId))}`),
    "Failed to load approvals",
  );
}

export async function approveOutreachApproval(approvalId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ ok?: boolean; approval?: OutreachApproval }>(
    await ceApi(
      `/api/outreach/approvals/${encodeURIComponent(approvalId)}/approve${qs(workspaceParams(workspaceId))}`,
      { method: "POST" },
    ),
    "Failed to approve send",
  );
}

export async function rejectOutreachApproval(approvalId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ ok?: boolean; approval?: OutreachApproval }>(
    await ceApi(
      `/api/outreach/approvals/${encodeURIComponent(approvalId)}/reject${qs(workspaceParams(workspaceId))}`,
      { method: "POST" },
    ),
    "Failed to reject send",
  );
}

export async function processOutreachDue(workspaceId = DEFAULT_WORKSPACE, dryRun = false) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/outreach/process-due${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dry_run: dryRun, limit: 50 }),
    }),
    "Failed to process due enrollments",
  );
}

export async function importCompaniesHouseLead(
  body: {
    company_number: string;
    company_name: string;
    email?: string;
    tags?: string[];
    company_status?: string;
    registered_office?: string;
    sic_codes?: string[];
    officer_names?: string[];
  },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ lead?: OutreachLead; created?: boolean }>(
    await ceApi(`/api/outreach/companies-house/import-lead${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to import Companies House lead",
  );
}

export function createdCount(value: number | unknown[] | undefined): number {
  if (typeof value === "number") return value;
  if (Array.isArray(value)) return value.length;
  return 0;
}
