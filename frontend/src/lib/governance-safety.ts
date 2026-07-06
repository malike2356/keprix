import type { GovernanceStatus } from "@/lib/governance-api";
import { formatTimeAgo } from "@/lib/time-ago";

export type GovernanceKillState = {
  stop_agent?: boolean;
  lock_workspace?: boolean;
  disable_tools?: boolean;
  active_directives?: Array<{ type?: string; payload?: Record<string, unknown>; received_at?: string }>;
  updated_at?: string | null;
};

export type GovernanceSafetyLevel = "loading" | "unknown" | "ungoverned" | "governed" | "degraded" | "kill_active";

export type GovernanceSafetyView = {
  level: GovernanceSafetyLevel;
  label: string;
  tooltip: string;
  chipColor: "default" | "success" | "warning" | "error" | "info";
};

function killDirectiveSummary(kill: GovernanceKillState): string {
  const parts: string[] = [];
  if (kill.stop_agent) parts.push("agent stop");
  if (kill.lock_workspace) parts.push("workspace lock");
  if (kill.disable_tools) parts.push("tools disabled");
  if (!parts.length && kill.active_directives?.length) {
    return `${kill.active_directives.length} active directive(s)`;
  }
  return parts.join(", ");
}

export function isKillActive(kill?: GovernanceKillState | null): boolean {
  if (!kill) return false;
  return Boolean(
    kill.stop_agent ||
      kill.lock_workspace ||
      kill.disable_tools ||
      (kill.active_directives?.length ?? 0) > 0,
  );
}

export function deriveGovernanceSafety(status: GovernanceStatus | undefined, loading: boolean): GovernanceSafetyView {
  if (loading && !status) {
    return {
      level: "loading",
      label: "Governance",
      tooltip: "Loading governance safety status",
      chipColor: "default",
    };
  }

  if (!status) {
    return {
      level: "unknown",
      label: "Governance",
      tooltip: "Could not load governance safety status",
      chipColor: "default",
    };
  }

  const kill = status.kill_state;
  if (isKillActive(kill)) {
    const summary = kill ? killDirectiveSummary(kill) : "active directives";
    return {
      level: "kill_active",
      label: "Kill active",
      tooltip: `Governance kill directive active: ${summary}. Open governance settings for details.`,
      chipColor: "error",
    };
  }

  if (!status.connected) {
    return {
      level: "ungoverned",
      label: "Ungoverned",
      tooltip: "No governance provider is connected. Keprix is running without governance controls.",
      chipColor: "default",
    };
  }

  if (status.reporting_paused) {
    return {
      level: "degraded",
      label: "Degraded",
      tooltip: "Governance provider is connected but event reporting is paused after repeated delivery failures.",
      chipColor: "warning",
    };
  }

  if (status.last_heartbeat_ok === false) {
    const when = status.last_heartbeat_at ? formatTimeAgo(status.last_heartbeat_at) : "recently";
    return {
      level: "degraded",
      label: "Degraded",
      tooltip: `Governance provider is connected but the last heartbeat failed (${when}).`,
      chipColor: "warning",
    };
  }

  const heartbeat = status.last_heartbeat_at
    ? `Last heartbeat ${formatTimeAgo(status.last_heartbeat_at)}`
    : "Heartbeat pending";
  const policies = status.policies?.length ?? 0;

  return {
    level: "governed",
    label: "Governed",
    tooltip: `Governance connected. ${heartbeat}. ${policies} active polic${policies === 1 ? "y" : "ies"}.`,
    chipColor: "success",
  };
}

export const deriveScoutSafety = deriveGovernanceSafety;
