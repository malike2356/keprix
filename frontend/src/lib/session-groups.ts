import type { WorkspaceSession } from "@/lib/workspace-api";

export type SessionDateGroup = {
  label: string;
  items: WorkspaceSession[];
};

export function truncateSessionTitle(title: string, max = 40): string {
  const trimmed = title.trim() || "Conversation";
  return trimmed.length > max ? `${trimmed.slice(0, max)}...` : trimmed;
}

export function groupSessionsByDate(sessions: WorkspaceSession[]): SessionDateGroup[] {
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startYesterday = new Date(startToday.getTime() - 86_400_000);
  const startWeek = new Date(startToday.getTime() - 7 * 86_400_000);

  const buckets: Record<string, WorkspaceSession[]> = {
    Today: [],
    Yesterday: [],
    "Last 7 days": [],
    Older: [],
  };

  for (const session of sessions) {
    const raw = session.updated_at || session.created_at;
    const date = raw ? new Date(raw) : new Date(0);
    if (date >= startToday) {
      buckets.Today.push(session);
    } else if (date >= startYesterday) {
      buckets.Yesterday.push(session);
    } else if (date >= startWeek) {
      buckets["Last 7 days"].push(session);
    } else {
      buckets.Older.push(session);
    }
  }

  return (["Today", "Yesterday", "Last 7 days", "Older"] as const)
    .map((label) => ({ label, items: buckets[label] }))
    .filter((group) => group.items.length > 0);
}
