export type CrmEntityKind = "leads" | "contacts" | "accounts" | "deals" | "lists";

export type CrmEmail = string | { address?: string; primary?: boolean };

export type CrmRecord = {
  id: string;
  name?: string;
  display_name?: string;
  company_name?: string;
  company_number?: string;
  domain?: string;
  emails?: CrmEmail[];
  phones?: unknown[];
  source?: string | null;
  domain_pack?: string | null;
  stage?: string | null;
  status?: string | null;
  tags?: string[];
  scores?: Record<string, unknown> | null;
  assigned_agent?: string | null;
  last_touch_at?: string | null;
  account_id?: string | null;
  description?: string | null;
  version?: number;
  [key: string]: unknown;
};

export type CrmPage = {
  items: CrmRecord[];
  count: number;
  limit: number;
  offset: number;
  workspace_id?: string;
};

export type CrmStatus = {
  ok: boolean;
  workspace_id: string;
  counts: {
    accounts: number;
    leads: number;
    contacts: number;
    deals: number;
    lists: number;
    pending_approvals: number;
  };
};

export type CrmApproval = {
  id: string;
  kind?: string;
  subject?: string;
  status?: string;
  object_type?: string;
  object_id?: string;
  payload?: Record<string, unknown>;
  created_at?: string;
  [key: string]: unknown;
};

export type CrmActivity = {
  id: string;
  entity_type?: string;
  entity_id?: string;
  activity_type?: string;
  channel?: string | null;
  subject?: string | null;
  body?: string | null;
  created_at?: string;
  [key: string]: unknown;
};

export type CrmListDetail = {
  list: CrmRecord;
  members: CrmRecord[];
};

export const CRM_STAGES = [
  "discovered",
  "enriched",
  "listed",
  "approved",
  "enrolled",
  "contacted",
  "engaged",
  "qualified",
  "booked",
  "customer",
  "paying",
  "suppressed",
  "bounced",
  "do_not_contact",
  "lost",
] as const;

export const CRM_WORKSPACE = "default";

export function primaryEmail(row: CrmRecord | null | undefined): string {
  const emails = row?.emails;
  if (!Array.isArray(emails) || emails.length === 0) return "";
  for (const item of emails) {
    if (typeof item === "string" && item.trim()) return item.trim();
    if (item && typeof item === "object" && item.address) return String(item.address);
  }
  return "";
}

export function displayName(row: CrmRecord | null | undefined): string {
  if (!row) return "Untitled";
  return (
    String(row.name || row.display_name || row.company_name || row.domain || row.id || "Untitled").trim() ||
    "Untitled"
  );
}

export function companyLabel(row: CrmRecord | null | undefined): string {
  if (!row) return "";
  return String(row.company_name || row.domain || row.name || "").trim();
}

export function formatTouch(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function stageLabel(stage: string | null | undefined): string {
  if (!stage) return "unknown";
  return stage.replace(/_/g, " ");
}

export function singularKind(kind: CrmEntityKind): string {
  if (kind === "lists") return "list";
  return kind.slice(0, -1);
}
