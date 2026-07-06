import { ceApi } from "@/lib/ce-api";

export type EmailAccount = {
  id: string;
  label: string;
  email_address: string;
  is_active: boolean;
  last_polled_at?: string | null;
};

export type EmailMessage = {
  id: string;
  account_id: string;
  from_address: string;
  from_name?: string | null;
  subject: string;
  preview?: string | null;
  body_text?: string | null;
  is_read: boolean;
  is_starred: boolean;
  ai_summary?: string | null;
  ai_tags: string[];
  ai_priority: string;
  received_at: string;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(
      (payload as { detail?: string; error?: string }).detail ||
        (payload as { error?: string }).error ||
        fallback,
    );
  }
  return response.json();
}

export async function fetchEmailAccounts(): Promise<EmailAccount[]> {
  return parseJson(await ceApi("/api/email/accounts"), "Failed to load accounts");
}

export async function fetchInbox(limit = 50): Promise<EmailMessage[]> {
  return parseJson(await ceApi(`/api/email/inbox?limit=${limit}`), "Failed to load inbox");
}

export async function fetchEmail(emailId: string): Promise<EmailMessage> {
  return parseJson(await ceApi(`/api/email/${emailId}`), "Failed to load email");
}

export async function markEmailRead(emailId: string): Promise<void> {
  await parseJson(await ceApi(`/api/email/${emailId}/read`, { method: "PUT" }), "Failed to mark read");
}

export async function toggleEmailStar(emailId: string): Promise<{ is_starred: boolean }> {
  return parseJson(await ceApi(`/api/email/${emailId}/star`, { method: "PUT" }), "Failed to toggle star");
}

export async function triggerEmailSync(): Promise<{ synced?: number }> {
  return parseJson(await ceApi("/api/email/sync", { method: "POST" }), "Sync failed");
}

export async function fetchAiSummary(emailId: string): Promise<{ summary: string }> {
  return parseJson(
    await ceApi(`/api/email/${emailId}/ai-summary`, { method: "POST" }),
    "AI summary failed",
  );
}

export async function createAiReplyDraft(emailId: string): Promise<{ id: string; body: string; subject: string }> {
  return parseJson(
    await ceApi(`/api/email/${emailId}/ai-reply-draft`, { method: "POST" }),
    "AI draft failed",
  );
}

export async function createReplyDraft(emailId: string): Promise<{ id: string; body: string; subject: string }> {
  return parseJson(
    await ceApi(`/api/email/${emailId}/reply`, { method: "POST" }),
    "Reply draft failed",
  );
}

export async function sendEmail(body: {
  to_addresses: string[];
  subject: string;
  body: string;
  account_id?: string;
}): Promise<void> {
  await parseJson(
    await ceApi("/api/email/send", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Send failed",
  );
}
