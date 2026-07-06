import { ceApi } from "@/lib/ce-api";

export type NotifyExternalConfig = {
  smtp_host?: string | null;
  smtp_port?: number;
  smtp_use_tls?: boolean;
  smtp_username?: string | null;
  smtp_from_email?: string | null;
  smtp_from_name?: string | null;
  smtp_password_vault_id?: string;
  max_retries?: number;
};

export async function fetchNotifyExternalConfig(): Promise<NotifyExternalConfig> {
  const response = await ceApi("/api/notify-external/config");
  if (!response.ok) {
    throw new Error("Failed to load external notification config");
  }
  return response.json();
}

export async function saveNotifyExternalConfig(config: Partial<NotifyExternalConfig> & { smtp_password?: string }) {
  const response = await ceApi("/api/notify-external/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to save config");
  }
  return response.json();
}

export async function sendNotifyExternalTestEmail(to_email: string) {
  const response = await ceApi("/api/notify-external/test-email", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ to_email }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Test email failed");
  }
  return response.json();
}

export async function listNotifyExternalDeliveries() {
  const response = await ceApi("/api/notify-external/notifications");
  if (!response.ok) {
    throw new Error("Failed to load delivery log");
  }
  return response.json();
}
