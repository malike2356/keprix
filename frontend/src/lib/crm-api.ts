import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";
import type {
  CrmActivity,
  CrmApproval,
  CrmEntityKind,
  CrmListDetail,
  CrmPage,
  CrmRecord,
  CrmStatus,
} from "@/components/crm/types";

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

export async function fetchCrmStatus(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<CrmStatus>(
    await ceApi(`/api/crm/status${qs(workspaceParams(workspaceId))}`),
    "Failed to load CRM status",
  );
}

export async function fetchCrmApprovals(workspaceId = DEFAULT_WORKSPACE, kind?: string) {
  return parseJson<{ items: CrmApproval[]; count: number }>(
    await ceApi(`/api/crm/approvals${qs({ ...workspaceParams(workspaceId), kind })}`),
    "Failed to load CRM approvals",
  );
}

export async function approveCrmApproval(approvalId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ ok: boolean; approval: CrmApproval }>(
    await ceApi(
      `/api/crm/approvals/${encodeURIComponent(approvalId)}/approve${qs(workspaceParams(workspaceId))}`,
      { method: "POST" },
    ),
    "Failed to approve CRM item",
  );
}

export async function rejectCrmApproval(approvalId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ ok: boolean; approval: CrmApproval }>(
    await ceApi(
      `/api/crm/approvals/${encodeURIComponent(approvalId)}/reject${qs(workspaceParams(workspaceId))}`,
      { method: "POST" },
    ),
    "Failed to reject CRM item",
  );
}

export async function fetchCrmCollection(
  kind: CrmEntityKind,
  workspaceId = DEFAULT_WORKSPACE,
  opts?: { q?: string; stage?: string; source?: string; limit?: number; offset?: number },
) {
  return parseJson<CrmPage>(
    await ceApi(
      `/api/crm/${kind}${qs({
        ...workspaceParams(workspaceId),
        q: opts?.q,
        stage: opts?.stage,
        source: opts?.source,
        limit: opts?.limit ?? 100,
        offset: opts?.offset ?? 0,
      })}`,
    ),
    `Failed to load CRM ${kind}`,
  );
}

export async function fetchCrmRecord(kind: CrmEntityKind, id: string, workspaceId = DEFAULT_WORKSPACE) {
  const singular = kind.endsWith("s") ? kind.slice(0, -1) : kind;
  const payload = await parseJson<Record<string, CrmRecord>>(
    await ceApi(`/api/crm/${kind}/${encodeURIComponent(id)}${qs(workspaceParams(workspaceId))}`),
    `Failed to load CRM ${singular}`,
  );
  return { record: payload[singular] ?? payload.list ?? Object.values(payload)[0], raw: payload };
}

export async function createCrmRecord(
  kind: CrmEntityKind,
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/crm/${kind}${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    `Failed to create CRM ${kind}`,
  );
}

export async function patchCrmRecord(
  kind: CrmEntityKind,
  id: string,
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/crm/${kind}/${encodeURIComponent(id)}${qs(workspaceParams(workspaceId))}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    `Failed to update CRM ${kind}`,
  );
}

export async function deleteCrmRecord(kind: CrmEntityKind, id: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/crm/${kind}/${encodeURIComponent(id)}${qs(workspaceParams(workspaceId))}`, {
      method: "DELETE",
    }),
    `Failed to delete CRM ${kind}`,
  );
}

export async function fetchCrmListDetail(listId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<CrmListDetail>(
    await ceApi(`/api/crm/lists/${encodeURIComponent(listId)}${qs(workspaceParams(workspaceId))}`),
    "Failed to load CRM list",
  );
}

export async function addCrmListMember(
  listId: string,
  body: { member_type: "lead" | "contact"; member_id: string; stage?: string },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ membership: CrmRecord }>(
    await ceApi(`/api/crm/lists/${encodeURIComponent(listId)}/members${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to add list member",
  );
}

export async function fetchCrmActivities(
  workspaceId = DEFAULT_WORKSPACE,
  opts?: { entity_type?: string; entity_id?: string },
) {
  return parseJson<{ items: CrmActivity[]; count: number }>(
    await ceApi(
      `/api/crm/activities${qs({
        ...workspaceParams(workspaceId),
        entity_type: opts?.entity_type,
        entity_id: opts?.entity_id,
      })}`,
    ),
    "Failed to load CRM activities",
  );
}

export async function createCrmActivity(
  body: {
    entity_type: string;
    entity_id: string;
    activity_type: string;
    channel?: string;
    subject?: string;
    body?: string;
  },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ activity: CrmActivity }>(
    await ceApi(`/api/crm/activities${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to create CRM activity",
  );
}

export async function bulkDeleteCrmLeads(
  ids: string[],
  opts: { preview?: boolean; reason?: string } = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ preview: boolean; count: number; deleted?: string[]; ids?: string[] }>(
    await ceApi(`/api/crm/leads/bulk-delete${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ids,
        preview: opts.preview ?? false,
        reason: opts.reason,
      }),
    }),
    "Failed to bulk delete CRM leads",
  );
}

/* Soft Wall safety surfaces (operator GUI gap closeout 469-474) */

export async function fetchCrmDeliverability(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{
    sender_readiness: CrmRecord[];
    kill_switches: CrmRecord[];
    rates: Record<string, number | string>;
    thresholds: Record<string, number>;
    breaches: string[];
    checklist: Record<string, boolean>;
    soft_wall_block_cold_send: boolean;
    soft_wall_block_reason: string | null;
  }>(
    await ceApi(`/api/crm/deliverability${qs(workspaceParams(workspaceId))}`),
    "Failed to load deliverability",
  );
}

export async function upsertSenderReadiness(
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ sender_readiness: CrmRecord }>(
    await ceApi(`/api/crm/deliverability/sender-readiness${qs(workspaceParams(workspaceId))}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "Failed to save sender readiness",
  );
}

export async function fetchCrmOutbox(workspaceId = DEFAULT_WORKSPACE, status?: string) {
  return parseJson<{ items: CrmRecord[]; count: number; dead_letter_count?: number }>(
    await ceApi(`/api/crm/outbox${qs({ ...workspaceParams(workspaceId), status })}`),
    "Failed to load outbox",
  );
}

export async function retryCrmOutbox(
  outboxId: string,
  opts: { force?: boolean; approval_id?: string } = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{
    blocked?: boolean;
    outbox?: CrmRecord;
    approval?: CrmApproval;
    idempotency_key?: string;
  }>(
    await ceApi(`/api/crm/outbox/${encodeURIComponent(outboxId)}/retry${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify(opts),
    }),
    "Failed to retry outbox item",
  );
}

export async function cancelCrmOutbox(outboxId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ outbox: CrmRecord }>(
    await ceApi(`/api/crm/outbox/${encodeURIComponent(outboxId)}/cancel${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
    "Failed to cancel outbox item",
  );
}

export async function fetchCrmSuppressions(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ items: CrmRecord[]; count: number }>(
    await ceApi(`/api/crm/suppressions${qs(workspaceParams(workspaceId))}`),
    "Failed to load suppressions",
  );
}

export async function createCrmSuppression(
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ suppression: CrmRecord }>(
    await ceApi(`/api/crm/suppressions${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to create suppression",
  );
}

export async function deleteCrmSuppression(
  entryId: string,
  opts: { force?: boolean; approval_id?: string } = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ blocked?: boolean; suppression?: CrmRecord; approval?: CrmApproval }>(
    await ceApi(
      `/api/crm/suppressions/${encodeURIComponent(entryId)}${qs({
        ...workspaceParams(workspaceId),
        force: opts.force,
        approval_id: opts.approval_id,
      })}`,
      { method: "DELETE" },
    ),
    "Failed to undo suppression",
  );
}

export async function bulkCrmSuppressions(
  rows: Array<Record<string, unknown>>,
  opts: { preview?: boolean; force?: boolean; approval_id?: string } = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{
    preview?: boolean;
    blocked?: boolean;
    count: number;
    sample?: unknown[];
    items?: CrmRecord[];
    approval?: CrmApproval;
  }>(
    await ceApi(`/api/crm/suppressions/bulk${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify({
        rows,
        preview: opts.preview ?? true,
        force: opts.force,
        approval_id: opts.approval_id,
      }),
    }),
    "Failed bulk suppressions",
  );
}

export async function fetchCrmContactability(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ items: CrmRecord[]; count: number }>(
    await ceApi(`/api/crm/contactability${qs(workspaceParams(workspaceId))}`),
    "Failed to load contactability",
  );
}

export async function upsertCrmContactability(
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ decision: CrmRecord }>(
    await ceApi(`/api/crm/contactability${qs(workspaceParams(workspaceId))}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "Failed to save contactability",
  );
}

export async function fetchCrmMerges(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ items: CrmRecord[]; count: number }>(
    await ceApi(`/api/crm/merges${qs(workspaceParams(workspaceId))}`),
    "Failed to load merges",
  );
}

export async function applyCrmMerge(
  suggestionId: string,
  opts: { survivor_id?: string; force?: boolean; approval_id?: string } = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ blocked?: boolean; approval?: CrmApproval; [key: string]: unknown }>(
    await ceApi(`/api/crm/merges/${encodeURIComponent(suggestionId)}/apply${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify(opts),
    }),
    "Failed to apply merge",
  );
}

export async function rejectCrmMerge(
  suggestionId: string,
  reason?: string,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ ok: boolean; suggestion: CrmRecord }>(
    await ceApi(`/api/crm/merges/${encodeURIComponent(suggestionId)}/reject${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
    "Failed to reject merge",
  );
}

export async function fetchCrmKillSwitches(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ items: CrmRecord[] }>(
    await ceApi(`/api/crm/kill-switches${qs(workspaceParams(workspaceId))}`),
    "Failed to load kill switches",
  );
}

export async function upsertCrmKillSwitch(
  body: {
    scope: string;
    scope_id?: string | null;
    enabled: boolean;
    reason?: string;
    force?: boolean;
    approval_id?: string;
  },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ blocked?: boolean; kill_switch?: CrmRecord; approval?: CrmApproval }>(
    await ceApi(`/api/crm/kill-switches${qs(workspaceParams(workspaceId))}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "Failed to update kill switch",
  );
}

/* Discovery (prompts 436-441) */

export type CrmDiscoveryJob = CrmRecord & {
  adapter?: string;
  status?: string;
  cost_estimate?: number | null;
  list_id?: string | null;
  error?: string | null;
  params?: Record<string, unknown>;
  result_counts?: Record<string, unknown>;
  checkpoint?: Record<string, unknown>;
};

export async function fetchDiscoveryAdapters(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{
    items: Array<Record<string, unknown>>;
    health: Array<{
      name: string;
      status?: string;
      message?: string;
      enabled?: boolean;
      configured?: boolean;
    }>;
    count: number;
  }>(
    await ceApi(`/api/crm/discovery/adapters${qs(workspaceParams(workspaceId))}`),
    "Failed to load discovery adapters",
  );
}

export async function runDiscoveryJob(
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{
    job?: CrmDiscoveryJob;
    materialize?: {
      blocked?: boolean;
      list_id?: string;
      approval?: CrmApproval;
      [key: string]: unknown;
    };
    deep_links?: Record<string, string | null | undefined>;
    refused?: boolean;
    message?: string;
    [key: string]: unknown;
  }>(
    await ceApi(`/api/crm/discovery/run${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to run discovery",
  );
}

export async function fetchCrmJobs(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{
    discovery_jobs: CrmDiscoveryJob[];
    enrichment_jobs: CrmRecord[];
    count: number;
  }>(await ceApi(`/api/crm/jobs${qs(workspaceParams(workspaceId))}`), "Failed to load CRM jobs");
}

export async function fetchCrmJob(jobId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{
    kind: string;
    job: CrmDiscoveryJob;
    adapter_health?: {
      status?: string;
      message?: string;
      name?: string;
    };
    deep_links?: Record<string, string | null | undefined>;
  }>(
    await ceApi(`/api/crm/jobs/${encodeURIComponent(jobId)}${qs(workspaceParams(workspaceId))}`),
    "Failed to load CRM job",
  );
}

export async function cancelCrmJob(jobId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ job: CrmDiscoveryJob }>(
    await ceApi(
      `/api/crm/jobs/${encodeURIComponent(jobId)}/cancel${qs(workspaceParams(workspaceId))}`,
      { method: "POST", body: JSON.stringify({}) },
    ),
    "Failed to cancel job",
  );
}

export async function runCrmJob(
  jobId: string,
  opts: { force?: boolean; approval_id?: string; materialize?: boolean } = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(
      `/api/crm/jobs/${encodeURIComponent(jobId)}/run${qs(workspaceParams(workspaceId))}`,
      { method: "POST", body: JSON.stringify(opts) },
    ),
    "Failed to run job",
  );
}

export async function materializeCrmJob(
  jobId: string,
  opts: { force?: boolean; approval_id?: string; list_name?: string } = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(
      `/api/crm/jobs/${encodeURIComponent(jobId)}/materialize${qs(workspaceParams(workspaceId))}`,
      { method: "POST", body: JSON.stringify(opts) },
    ),
    "Failed to materialize job",
  );
}

export async function retryCrmJob(
  jobId: string,
  opts: { force?: boolean; approval_id?: string; materialize?: boolean } = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(
      `/api/crm/jobs/${encodeURIComponent(jobId)}/retry${qs(workspaceParams(workspaceId))}`,
      { method: "POST", body: JSON.stringify(opts) },
    ),
    "Failed to retry job",
  );
}

/* Sheet preprocess (prompt 434) */

export type SheetEnrichJob = CrmRecord & {
  metrics?: {
    blank_cells?: number;
    proposed_fills?: number;
    cells_filled?: number;
    cells_skipped?: number;
    cost_estimate?: number | null;
    row_count?: number;
  };
  proposal?: Record<string, unknown>;
  apply_result?: Record<string, unknown>;
  deep_link?: string;
  sheet_type?: string;
  source_path?: string;
  output_path?: string;
  cost_estimate?: number | null;
};

export async function uploadCrmSheet(file: File, workspaceId = DEFAULT_WORKSPACE) {
  const form = new FormData();
  form.append("file", file);
  return parseJson<{ upload: { upload_id: string; filename: string; path: string; size_bytes: number } }>(
    await ceApi(`/api/crm/sheets/upload${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: form,
    }),
    "Failed to upload spreadsheet",
  );
}

export async function importCrmGoogleSheet(
  body: { spreadsheet_id: string; range_name?: string; title?: string },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ upload: { upload_id: string; filename: string; path: string; size_bytes: number } }>(
    await ceApi(`/api/crm/sheets/import/google-sheet${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to import Google Sheet",
  );
}

export async function proposeCrmSheet(
  body: {
    upload_id?: string;
    source_path?: string;
    user_schema?: Record<string, string | Record<string, unknown>>;
    domain_pack?: string;
    context?: string;
    build_crm_plan?: boolean;
  },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ enrichment_job: SheetEnrichJob }>(
    await ceApi(`/api/crm/sheets/propose${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to propose sheet enrichment",
  );
}

export async function fetchCrmSheetJob(jobId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ enrichment_job: SheetEnrichJob }>(
    await ceApi(`/api/crm/sheets/${encodeURIComponent(jobId)}${qs(workspaceParams(workspaceId))}`),
    "Failed to load enrichment job",
  );
}

export async function listCrmSheetJobs(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ items: SheetEnrichJob[]; count: number }>(
    await ceApi(`/api/crm/sheets${qs(workspaceParams(workspaceId))}`),
    "Failed to list sheet jobs",
  );
}

export async function applyCrmSheetJob(
  jobId: string,
  opts: { force?: boolean; approval_id?: string; upsert_crm?: boolean } = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{
    blocked?: boolean;
    error_code?: string;
    approval?: CrmApproval;
    enrichment_job?: SheetEnrichJob;
    list_id?: string | null;
    list_deep_link?: string | null;
    leads_deep_link?: string;
    deep_link?: string;
  }>(
    await ceApi(`/api/crm/sheets/${encodeURIComponent(jobId)}/apply${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify({
        force: opts.force,
        approval_id: opts.approval_id,
        upsert_crm: opts.upsert_crm ?? true,
      }),
    }),
    "Failed to apply sheet enrichment",
  );
}

export function crmSheetDownloadUrl(jobId: string, format: "xlsx" | "csv" = "xlsx", workspaceId = DEFAULT_WORKSPACE) {
  return `/api/crm/sheets/${encodeURIComponent(jobId)}/download${qs({ ...workspaceParams(workspaceId), format })}`;
}

export async function publishCrmGoogleSheet(jobId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ spreadsheet_id?: string; spreadsheet_url?: string }>(
    await ceApi(`/api/crm/sheets/${encodeURIComponent(jobId)}/publish/google-sheet${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
    }),
    "Failed to publish Google Sheet",
  );
}

/* Funnel enroll / inbox / workflows (442-448) */

export async function preflightCrmListEnroll(
  listId: string,
  body: { sequence_id: string; campaign_id?: string },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/crm/lists/${encodeURIComponent(listId)}/enroll-preflight${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed enroll preflight",
  );
}

export async function enrollCrmList(
  listId: string,
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/crm/lists/${encodeURIComponent(listId)}/enroll${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to enroll CRM list",
  );
}

export async function fetchCrmInbox(
  workspaceId = DEFAULT_WORKSPACE,
  opts?: { status?: string; kind?: string },
) {
  return parseJson<{ items: CrmRecord[]; count: number }>(
    await ceApi(
      `/api/crm/inbox${qs({
        ...workspaceParams(workspaceId),
        status: opts?.status,
        kind: opts?.kind,
      })}`,
    ),
    "Failed to load CRM inbox",
  );
}

export async function claimCrmInboxItem(itemId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ item: CrmRecord }>(
    await ceApi(`/api/crm/inbox/${encodeURIComponent(itemId)}/claim${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
    "Failed to claim inbox item",
  );
}

export async function pauseCrmInboxItem(itemId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ item: CrmRecord }>(
    await ceApi(`/api/crm/inbox/${encodeURIComponent(itemId)}/pause${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
    "Failed to pause inbox item",
  );
}

export async function resumeCrmInboxItem(itemId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ item: CrmRecord }>(
    await ceApi(`/api/crm/inbox/${encodeURIComponent(itemId)}/resume${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
    "Failed to resume inbox item",
  );
}

export async function fetchCrmWorkflows(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ items: CrmRecord[]; count: number }>(
    await ceApi(`/api/crm/workflows${qs(workspaceParams(workspaceId))}`),
    "Failed to load workflows",
  );
}

export async function setCrmWorkflowStatus(
  sequenceId: string,
  status: string,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/crm/workflows/${encodeURIComponent(sequenceId)}/status${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
    "Failed to update workflow status",
  );
}

export async function fetchCrmFunnel(
  workspaceId = DEFAULT_WORKSPACE,
  opts?: { campaign_id?: string; pack?: string; days?: number },
) {
  return parseJson<{
    metrics: Record<string, number>;
    deliverability_strip?: Record<string, unknown>;
    deep_links?: Record<string, string>;
  }>(
    await ceApi(
      `/api/crm/funnel${qs({
        ...workspaceParams(workspaceId),
        campaign_id: opts?.campaign_id,
        pack: opts?.pack,
        days: opts?.days,
      })}`,
    ),
    "Failed to load CRM funnel",
  );
}

export async function fetchCrmSettingsSummary(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{
    kill_switches: CrmRecord[];
    policy: Record<string, unknown>;
    deliverability: Record<string, unknown>;
    cadence_defaults: Record<string, unknown>;
  }>(
    await ceApi(`/api/crm/settings/summary${qs(workspaceParams(workspaceId))}`),
    "Failed to load CRM settings",
  );
}

export async function fetchCrmDemoSeedStatus(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{
    ok: boolean;
    workspace_id: string;
    present: boolean;
    counts: Record<string, number>;
    hint?: string;
  }>(
    await ceApi(`/api/crm/demo-seed/status${qs(workspaceParams(workspaceId))}`),
    "Failed to load CRM demo-seed status",
  );
}

export async function purgeCrmDemoSeed(
  body: { force?: boolean; approval_id?: string } = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{
    ok?: boolean;
    blocked?: boolean;
    error_code?: string;
    approval?: CrmApproval;
    present?: boolean;
    counts?: Record<string, number>;
    removed?: Record<string, number>;
    remaining?: Record<string, number>;
    hint?: string;
  }>(
    await ceApi(`/api/crm/demo-seed/purge${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to purge CRM demo-seed data",
  );
}

export type CrmConnectionSlotStatus = {
  slot_id: string;
  group: string;
  label: string;
  description: string;
  secret: boolean;
  configured: boolean;
  source: string | null;
  masked: string | null;
  env_fallbacks: string[];
  updated_at?: string | null;
};

export type CrmConnectionFlagStatus = {
  flag_id: string;
  group: string;
  label: string;
  description: string;
  env: string;
  enabled: boolean;
  workspace_enabled: boolean;
  env_enabled: boolean;
};

export async function fetchCrmConnections(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{
    catalog: {
      groups: Record<
        string,
        Array<{
          slot_id: string;
          label: string;
          description: string;
          secret: boolean;
          env_fallbacks: string[];
          param_key: string | null;
        }>
      >;
      flags: Array<{ flag_id: string; group: string; label: string; description: string; env: string }>;
    };
    status: {
      workspace_id: string;
      groups: Record<string, CrmConnectionSlotStatus[]>;
      flags: CrmConnectionFlagStatus[];
      ready_groups: Record<string, boolean>;
    };
  }>(
    await ceApi(`/api/crm/connections${qs(workspaceParams(workspaceId))}`),
    "Failed to load CRM connections",
  );
}

export async function putCrmConnectionCredential(
  body: { slot_id: string; value: string; label?: string },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ ok: boolean; slot: CrmConnectionSlotStatus }>(
    await ceApi(`/api/crm/connections/credentials${qs(workspaceParams(workspaceId))}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "Failed to save credential",
  );
}

export async function deleteCrmConnectionCredential(slotId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ ok: boolean; slot_id: string; deleted: boolean }>(
    await ceApi(
      `/api/crm/connections/credentials/${encodeURIComponent(slotId)}${qs(workspaceParams(workspaceId))}`,
      { method: "DELETE" },
    ),
    "Failed to delete credential",
  );
}

export async function putCrmConnectionFlag(
  body: { flag_id: string; enabled: boolean },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ ok: boolean; flags: CrmConnectionFlagStatus[] }>(
    await ceApi(`/api/crm/connections/flags${qs(workspaceParams(workspaceId))}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "Failed to update feature flag",
  );
}

export async function fetchCrmConsents(workspaceId = DEFAULT_WORKSPACE, subjectId?: string) {
  return parseJson<{ items: CrmRecord[]; count: number }>(
    await ceApi(
      `/api/crm/consents${qs({ ...workspaceParams(workspaceId), subject_id: subjectId })}`,
    ),
    "Failed to load consents",
  );
}

export async function createCrmConsent(body: Record<string, unknown>, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ consent: CrmRecord }>(
    await ceApi(`/api/crm/consents${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to create consent",
  );
}

export async function offerCrmBooking(
  kind: "leads" | "contacts",
  id: string,
  body: Record<string, unknown> = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/crm/${kind}/${encodeURIComponent(id)}/offer-booking${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to offer booking",
  );
}

export async function exportCrmSubject(
  kind: "leads" | "contacts",
  id: string,
  opts: { force?: boolean; approval_id?: string } = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/crm/${kind}/${encodeURIComponent(id)}/export${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify(opts),
    }),
    "Failed subject export",
  );
}

/* Visual CRM (prompts 506-515) */

export async function fetchCrmVisualContract() {
  return parseJson<Record<string, unknown>>(
    await ceApi("/api/crm/visual/contract"),
    "Failed to load visual contract",
  );
}

export async function fetchCrmPipelineBoard(
  workspaceId = DEFAULT_WORKSPACE,
  opts?: Record<string, string | number | boolean | undefined | null>,
) {
  return parseJson<{
    lanes: Array<Record<string, unknown>>;
    columns: Record<string, Array<Record<string, unknown>>>;
    stages: string[];
    saved_views: Array<Record<string, unknown>>;
    filters: Record<string, unknown>;
    totals: Record<string, number>;
    [key: string]: unknown;
  }>(
    await ceApi(
      `/api/crm/visual/pipeline-board${qs({ ...workspaceParams(workspaceId), ...(opts || {}) })}`,
    ),
    "Failed to load pipeline board",
  );
}

export async function previewCrmStageTransition(
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/crm/visual/pipeline-board/preview-transition${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to preview stage transition",
  );
}

export async function commitCrmStageTransition(
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/crm/visual/pipeline-board/transition${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to commit stage transition",
  );
}

export async function fetchCrmVisualWorkflow(workflowId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{
    graph: Record<string, unknown>;
    validation: Record<string, unknown>;
    palette: Array<Record<string, unknown>>;
    templates: Array<Record<string, unknown>>;
  }>(
    await ceApi(
      `/api/crm/visual/workflows/${encodeURIComponent(workflowId)}${qs(workspaceParams(workspaceId))}`,
    ),
    "Failed to load workflow graph",
  );
}

export async function saveCrmVisualWorkflow(
  workflowId: string,
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(
      `/api/crm/visual/workflows/${encodeURIComponent(workflowId)}${qs(workspaceParams(workspaceId))}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    ),
    "Failed to save workflow graph",
  );
}

export async function validateCrmVisualWorkflow(
  workflowId: string,
  graph?: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(
      `/api/crm/visual/workflows/${encodeURIComponent(workflowId)}/validate${qs(workspaceParams(workspaceId))}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ graph }),
      },
    ),
    "Failed to validate workflow",
  );
}

export async function simulateCrmVisualWorkflow(
  workflowId: string,
  body: Record<string, unknown> = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(
      `/api/crm/visual/workflows/${encodeURIComponent(workflowId)}/simulate${qs(workspaceParams(workspaceId))}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    ),
    "Failed to simulate workflow",
  );
}

export async function publishCrmVisualWorkflow(
  workflowId: string,
  reason?: string,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(
      `/api/crm/visual/workflows/${encodeURIComponent(workflowId)}/publish${qs(workspaceParams(workspaceId))}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      },
    ),
    "Failed to publish workflow",
  );
}

export async function fetchCrmVisualRun(runId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{
    run: Record<string, unknown>;
    node_states: Record<string, Record<string, unknown>>;
    graph: Record<string, unknown> | null;
    timeline: Array<Record<string, unknown>>;
    animation_policy: Record<string, unknown>;
  }>(
    await ceApi(`/api/crm/visual/runs/${encodeURIComponent(runId)}${qs(workspaceParams(workspaceId))}`),
    "Failed to load run",
  );
}

export async function fetchCrmVisualRunEvents(
  runId: string,
  cursor = 0,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ cursor: number; events: Array<Record<string, unknown>> }>(
    await ceApi(
      `/api/crm/visual/runs/${encodeURIComponent(runId)}/events${qs({
        ...workspaceParams(workspaceId),
        cursor,
      })}`,
    ),
    "Failed to load run events",
  );
}

export async function stepCrmVisualRun(runId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<Record<string, unknown>>(
    await ceApi(
      `/api/crm/visual/runs/${encodeURIComponent(runId)}/step${qs(workspaceParams(workspaceId))}`,
      { method: "POST", body: JSON.stringify({}) },
    ),
    "Failed to step run",
  );
}

export async function createCrmVisualRun(
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ run: Record<string, unknown> }>(
    await ceApi(`/api/crm/visual/runs${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to create run",
  );
}

export async function fetchCrmNodeInspector(
  opts: { workflow_id: string; node_id: string; mode?: string; run_id?: string },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(
      `/api/crm/visual/inspector${qs({
        ...workspaceParams(workspaceId),
        workflow_id: opts.workflow_id,
        node_id: opts.node_id,
        mode: opts.mode || "design",
        run_id: opts.run_id,
      })}`,
    ),
    "Failed to load node inspector",
  );
}

export async function createCrmSupportBundle(
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/crm/visual/support-bundle${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to create support bundle",
  );
}

export async function fetchCrmMetricsDefinitions() {
  return parseJson<Record<string, unknown>>(
    await ceApi("/api/crm/visual/metrics/definitions"),
    "Failed to load metric definitions",
  );
}

export async function queryCrmMetrics(
  body: Record<string, unknown> = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{
    measures: Record<string, Record<string, unknown>>;
    guards: Record<string, Record<string, unknown>>;
    funnel: Array<Record<string, unknown>>;
    definition_version: string;
    freshness: string;
    incomplete_history: boolean;
    cohort_label: string;
    attribution_label: string;
    notes: string[];
    [key: string]: unknown;
  }>(
    await ceApi(`/api/crm/visual/metrics/query${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to query CRM metrics",
  );
}

export async function backfillCrmMetrics(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/crm/visual/metrics/backfill${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
    "Failed to backfill metrics",
  );
}

export async function fetchCrmOpsCentre(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{
    panels: Record<string, unknown>;
    alerts: Array<Record<string, unknown>>;
    transport: Record<string, unknown>;
    generated_at: string;
    [key: string]: unknown;
  }>(
    await ceApi(`/api/crm/visual/ops${qs(workspaceParams(workspaceId))}`),
    "Failed to load ops centre",
  );
}

export async function fetchCrmA11yPerformance() {
  return parseJson<Record<string, unknown>>(
    await ceApi("/api/crm/visual/a11y-performance"),
    "Failed to load a11y/performance contract",
  );
}

export type CrmIcpDefinition = {
  id: string;
  name?: string;
  version?: number;
  pack?: string;
  include_rules?: unknown[];
  exclude_rules?: unknown[];
  geography?: unknown[];
  size_band?: string | null;
  keywords?: unknown[];
  sic_codes?: unknown[];
  notes?: string | null;
  active?: boolean;
  parent_id?: string | null;
};

export async function fetchCrmIcps(workspaceId = DEFAULT_WORKSPACE, name?: string) {
  return parseJson<{
    items: CrmIcpDefinition[];
    count: number;
    active: CrmIcpDefinition | null;
  }>(
    await ceApi(`/api/crm/icp${qs({ ...workspaceParams(workspaceId), name })}`),
    "Failed to load ICP definitions",
  );
}

export async function createCrmIcp(body: Record<string, unknown>, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ icp: CrmIcpDefinition }>(
    await ceApi(`/api/crm/icp${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to create ICP",
  );
}

export async function reviseCrmIcp(
  icpId: string,
  body: Record<string, unknown>,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ icp: CrmIcpDefinition }>(
    await ceApi(`/api/crm/icp/${encodeURIComponent(icpId)}/revise${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to revise ICP",
  );
}

export async function activateCrmIcp(
  icpId: string,
  body: { force?: boolean; approval_id?: string } = {},
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{
    ok?: boolean;
    blocked?: boolean;
    approval?: CrmApproval;
    icp?: CrmIcpDefinition;
  }>(
    await ceApi(`/api/crm/icp/${encodeURIComponent(icpId)}/activate${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to activate ICP",
  );
}

export async function diffCrmIcps(leftId: string, rightId: string, workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{
    changes: Array<{ field: string; from: unknown; to: unknown }>;
    changed: boolean;
    left: { id?: string; name?: string; version?: number };
    right: { id?: string; name?: string; version?: number };
  }>(
    await ceApi(
      `/api/crm/icp/${encodeURIComponent(leftId)}/diff/${encodeURIComponent(rightId)}${qs(workspaceParams(workspaceId))}`,
    ),
    "Failed to diff ICP versions",
  );
}

export type CrmSlaInbox = {
  overdue: Array<Record<string, unknown>>;
  due_today: Array<Record<string, unknown>>;
  unassigned: Array<Record<string, unknown>>;
  counts: { overdue: number; due_today: number; unassigned: number };
};

export type CrmTeam = {
  id: string;
  name?: string;
  member_user_ids?: string[];
  round_robin_cursor?: number;
};

export async function fetchCrmSlaInbox(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<CrmSlaInbox>(
    await ceApi(`/api/crm/sla/inbox${qs(workspaceParams(workspaceId))}`),
    "Failed to load SLA inbox",
  );
}

export async function fetchCrmTeams(workspaceId = DEFAULT_WORKSPACE) {
  return parseJson<{ items: CrmTeam[]; count: number }>(
    await ceApi(`/api/crm/teams${qs(workspaceParams(workspaceId))}`),
    "Failed to load CRM teams",
  );
}

export async function createCrmTeam(
  body: { name: string; member_user_ids?: string[] },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ ok: boolean; team: CrmTeam }>(
    await ceApi(`/api/crm/teams${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to create team",
  );
}

export async function assignCrmOwner(
  body: {
    entity_type: string;
    entity_id: string;
    owner_user_id?: string;
    team_id?: string;
    mode?: string;
    sla_hours?: number | null;
    force?: boolean;
    approval_id?: string;
  },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{
    ok?: boolean;
    blocked?: boolean;
    approval?: CrmApproval;
    error?: string;
    entity?: Record<string, unknown>;
    mode?: string;
  }>(
    await ceApi(`/api/crm/assign${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to assign owner",
  );
}

export async function acquireCrmLock(
  body: { entity_type: string; entity_id: string; ttl_seconds?: number },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ ok?: boolean; conflict?: boolean; warning?: string; lock?: Record<string, unknown> }>(
    await ceApi(`/api/crm/locks${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to acquire lock",
  );
}

export async function releaseCrmLock(
  entityType: string,
  entityId: string,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ ok?: boolean }>(
    await ceApi(
      `/api/crm/locks${qs({ ...workspaceParams(workspaceId), entity_type: entityType, entity_id: entityId })}`,
      { method: "DELETE" },
    ),
    "Failed to release lock",
  );
}

export async function fetchCrmComments(
  entityType: string,
  entityId: string,
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ items: Array<Record<string, unknown>>; count: number }>(
    await ceApi(
      `/api/crm/comments${qs({
        ...workspaceParams(workspaceId),
        entity_type: entityType,
        entity_id: entityId,
      })}`,
    ),
    "Failed to load comments",
  );
}

export async function createCrmComment(
  body: { entity_type: string; entity_id: string; body: string; mentions?: string[] },
  workspaceId = DEFAULT_WORKSPACE,
) {
  return parseJson<{ ok: boolean; comment: Record<string, unknown> }>(
    await ceApi(`/api/crm/comments${qs(workspaceParams(workspaceId))}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to add comment",
  );
}
