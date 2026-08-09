import type { CrmRecord } from "@/components/crm/types";
import { primaryEmail } from "@/components/crm/types";

export const GRID_PREFS_KEY = "keprix.crm.leads.grid.v1";

export type LeadStatusKind =
  | "invalid_email"
  | "missing_email"
  | "suppressed"
  | "awaiting_approval"
  | "contacted"
  | "replied"
  | "booked"
  | "customer"
  | "paying"
  | "ok";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function leadStatusKinds(row: CrmRecord): LeadStatusKind[] {
  const kinds: LeadStatusKind[] = [];
  const email = primaryEmail(row);
  if (!email) kinds.push("missing_email");
  else if (!EMAIL_RE.test(email)) kinds.push("invalid_email");

  const stage = String(row.stage || row.pipeline_stage || "");
  if (stage === "suppressed" || row.suppression_reason) kinds.push("suppressed");
  if (stage === "contacted" || row.last_contacted_at) kinds.push("contacted");
  if (stage === "engaged" || row.last_reply_at) kinds.push("replied");
  if (stage === "booked") kinds.push("booked");
  if (stage === "customer") kinds.push("customer");
  if (stage === "paying") kinds.push("paying");
  if (row.awaiting_approval || row.soft_wall_pending) kinds.push("awaiting_approval");

  if (kinds.length === 0) kinds.push("ok");
  return kinds;
}

export function statusChipLabel(kind: LeadStatusKind): string {
  switch (kind) {
    case "invalid_email":
      return "Invalid email";
    case "missing_email":
      return "Missing email";
    case "suppressed":
      return "Suppressed";
    case "awaiting_approval":
      return "Awaiting approval";
    case "contacted":
      return "Contacted";
    case "replied":
      return "Replied";
    case "booked":
      return "Booked";
    case "customer":
      return "Customer";
    case "paying":
      return "Paying";
    default:
      return "Ready";
  }
}

export type GridDensity = "compact" | "comfortable" | "spacious";

export type LeadGridPrefs = {
  columnVisibilityModel?: Record<string, boolean>;
  columnOrder?: string[];
  columnWidths?: Record<string, number>;
  density?: GridDensity;
  sort?: string;
  order?: "asc" | "desc";
};

export function loadLeadGridPrefs(): LeadGridPrefs {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(GRID_PREFS_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as LeadGridPrefs;
  } catch {
    return {};
  }
}

export function saveLeadGridPrefs(prefs: LeadGridPrefs): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(GRID_PREFS_KEY, JSON.stringify(prefs));
}

export const SEO_COLUMN_FIELDS = [
  "company_name",
  "niche",
  "locality",
  "website",
  "name",
  "email",
  "phone",
  "google_reviews",
  "google_rating",
  "google_maps_url",
  "website_score",
  "ranks_top3",
  "weakness",
  "priority",
  "stage",
  "source_captured_at",
  "notes",
] as const;
