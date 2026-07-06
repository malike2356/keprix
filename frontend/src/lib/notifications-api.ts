import { ceApi } from "@/lib/ce-api";

export type InboxNotification = {
  id: string;
  notification_type: string;
  severity: string;
  title: string;
  message: string;
  href?: string | null;
  read: boolean;
  created_at: string;
  sensitive?: boolean;
};

export type NotificationPreferences = {
  workspace_id: string;
  user_id: string;
  channels_enabled: Record<string, boolean>;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  quiet_hours_timezone: string;
  digest_enabled: boolean;
  escalation_delay_minutes: number;
};

const WORKSPACE_ID = "default";

export async function fetchInbox(unreadOnly = false): Promise<{ notifications: InboxNotification[]; unread_count: number }> {
  const params = new URLSearchParams({ workspace_id: WORKSPACE_ID });
  if (unreadOnly) params.set("unread_only", "true");
  const response = await ceApi(`/api/notifications/inbox?${params.toString()}`);
  if (response.status === 404) {
    return { notifications: [], unread_count: 0 };
  }
  if (!response.ok) throw new Error("Failed to load inbox");
  return response.json();
}

export async function markNotificationRead(id: string) {
  const response = await ceApi(`/api/notifications/inbox/${id}/read?workspace_id=${WORKSPACE_ID}`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to mark notification read");
  return response.json();
}

export async function markAllNotificationsRead() {
  const response = await ceApi(`/api/notifications/inbox/read-all?workspace_id=${WORKSPACE_ID}`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to mark all read");
  return response.json();
}

export async function fetchNotificationPreferences(): Promise<NotificationPreferences> {
  const response = await ceApi(`/api/notifications/preferences?workspace_id=${WORKSPACE_ID}`);
  if (!response.ok) throw new Error("Failed to load notification preferences");
  return response.json();
}

export async function saveNotificationPreferences(patch: Partial<NotificationPreferences>) {
  const response = await ceApi(`/api/notifications/preferences?workspace_id=${WORKSPACE_ID}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!response.ok) throw new Error("Failed to save notification preferences");
  return response.json();
}

export async function fetchUnreadCount(): Promise<number> {
  try {
    const data = await fetchInbox(false);
    return data.unread_count ?? 0;
  } catch {
    return 0;
  }
}
