import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type UpgradeAlert = {
  id: string;
  target_version: string;
  severity: string;
  title: string;
  summary: string;
  risk_level: string;
  compatible: boolean;
  breaking_count: number;
  feature_count: number;
  release_url: string;
  dismissed: boolean;
  snoozed_until?: string | null;
  created_at: string;
};

export type UpgradeStatus = {
  product: string;
  current_version: string;
  alert_count: number;
  last_check_at?: string | null;
  alerts: UpgradeAlert[];
  preferences: UpgradeAlertPreferences;
  latest_changelog_version?: string;
  update_listed?: boolean;
  installable?: boolean;
  channel?: "current" | "stable" | "changelog_only";
  recommendation?: string;
};

export type UpgradeCheckNowResult = {
  update_available: boolean;
  current_version: string;
  target_version: string;
  installable?: boolean;
  recommendation?: string;
  alert?: UpgradeAlert;
  alerts?: UpgradeAlert[];
};

export type UpgradeAlertPreferences = {
  in_app_enabled: boolean;
  in_app_min_severity: string;
  email_enabled: boolean;
  email_min_severity: string;
  slack_enabled: boolean;
  slack_webhook_url: string;
  discord_enabled: boolean;
  discord_webhook_url: string;
  webhook_enabled: boolean;
  webhook_url: string;
  quiet_hours_enabled: boolean;
  quiet_hours_start: number;
  quiet_hours_end: number;
  auto_upgrade_policy: string;
  maintenance_day: number;
  maintenance_hour: number;
  require_tests_pass: boolean;
  notify_after_upgrade: boolean;
};

export type UpgradeWizardStep = {
  id: string;
  label: string;
  status: "done" | "failed" | "pending" | "running";
  detail: string;
  metrics?: { passed: number; total: number; duration_seconds: number };
};

export type UpgradeDryRunResult = {
  passed: boolean;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  warnings: string[];
  failed_test_details: string[];
  duration_seconds: number;
  recommendation: string;
};

export type UpgradeExecuteResult = {
  success: boolean;
  target_version: string;
  product: string;
  stage?: string | null;
  error?: string;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(parseApiErrorMessage(payload, fallback));
  return payload as T;
}

export async function fetchUpgradeStatus(): Promise<UpgradeStatus> {
  const response = await ceApi("/api/keprix/upgrade/status");
  return parseJson(response, "Failed to load upgrade status");
}

export async function checkUpgradeNow(): Promise<UpgradeCheckNowResult> {
  const response = await ceApi("/api/keprix/upgrade/check-now", { method: "POST" });
  return parseJson(response, "Upgrade check failed");
}

export async function fetchUpgradeWizard(target: string): Promise<{
  target: string;
  steps: UpgradeWizardStep[];
  check: Record<string, unknown>;
  changelog: Record<string, unknown>;
}> {
  const response = await ceApi(`/api/keprix/upgrade/wizard?target=${encodeURIComponent(target)}`);
  return parseJson(response, "Failed to load upgrade wizard");
}

export async function executeUpgrade(target: string, force = false): Promise<UpgradeExecuteResult> {
  const response = await ceApi("/api/keprix/upgrade/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target, force }),
  });
  return parseJson(response, "Upgrade failed");
}

export async function dryRunUpgrade(target: string, skipTests = false): Promise<UpgradeDryRunResult> {
  const response = await ceApi("/api/keprix/upgrade/dry-run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target, skip_tests: skipTests }),
  });
  return parseJson(response, "Dry run failed");
}

export async function rollbackUpgrade(force = false): Promise<Record<string, unknown>> {
  const response = await ceApi("/api/keprix/upgrade/rollback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ force }),
  });
  return parseJson(response, "Rollback failed");
}

export async function dismissUpgradeAlert(alertId: string): Promise<void> {
  const response = await ceApi(`/api/keprix/upgrade/alerts/${encodeURIComponent(alertId)}/dismiss`, {
    method: "POST",
  });
  await parseJson(response, "Failed to dismiss alert");
}

export async function snoozeUpgradeAlert(alertId: string, hours = 24): Promise<void> {
  const response = await ceApi(`/api/keprix/upgrade/alerts/${encodeURIComponent(alertId)}/snooze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hours }),
  });
  await parseJson(response, "Failed to snooze alert");
}

export async function fetchUpgradePreferences(): Promise<UpgradeAlertPreferences> {
  const response = await ceApi("/api/keprix/upgrade/notifications/preferences");
  const payload = await parseJson<{ preferences: UpgradeAlertPreferences }>(
    response,
    "Failed to load upgrade preferences",
  );
  return payload.preferences;
}

export async function saveUpgradePreferences(
  preferences: UpgradeAlertPreferences,
): Promise<UpgradeAlertPreferences> {
  const response = await ceApi("/api/keprix/upgrade/notifications/preferences", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(preferences),
  });
  const payload = await parseJson<{ preferences: UpgradeAlertPreferences }>(
    response,
    "Failed to save upgrade preferences",
  );
  return payload.preferences;
}

export function severityColor(severity: string): "error" | "warning" | "info" | "success" | "default" {
  switch (severity) {
    case "critical":
    case "high":
      return "error";
    case "medium":
      return "warning";
    case "low":
      return "info";
    default:
      return "default";
  }
}
