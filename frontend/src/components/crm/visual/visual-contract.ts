/** Visual CRM contract constants (prompt 506) mirrored for client labels. */

export const CRM_VISUAL_ROUTES = {
  overview: "/crm",
  pipeline: "/crm/pipeline",
  workflows: "/crm/workflows",
  analytics: "/crm/analytics",
  ops: "/crm/ops",
} as const;

export const RUNTIME_STATE_LABELS: Record<string, string> = {
  draft: "Draft",
  ready: "Ready",
  active: "Active",
  waiting: "Waiting",
  approval_required: "Approval required",
  paused: "Paused",
  succeeded: "Succeeded",
  partially_succeeded: "Partially succeeded",
  failed: "Failed",
  cancelled: "Cancelled",
  suppressed: "Suppressed",
  skipped: "Skipped",
  upcoming: "Upcoming",
};

export const RUNTIME_STATE_TONE: Record<
  string,
  "default" | "info" | "success" | "warning" | "error"
> = {
  draft: "default",
  ready: "info",
  active: "info",
  waiting: "warning",
  approval_required: "warning",
  paused: "default",
  succeeded: "success",
  partially_succeeded: "warning",
  failed: "error",
  cancelled: "default",
  suppressed: "error",
  skipped: "default",
  upcoming: "default",
};

export function stateLabel(state: string | null | undefined): string {
  if (!state) return "unknown";
  return RUNTIME_STATE_LABELS[state] || state.replace(/_/g, " ");
}
