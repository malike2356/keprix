import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type Contact = {
  id: string;
  display_name: string;
  given_name?: string | null;
  family_name?: string | null;
  emails: Array<{ address: string; label?: string; primary?: boolean }>;
  phones: Array<{ number: string; label?: string; primary?: boolean }>;
  addresses?: Array<Record<string, string>>;
  organisation?: string | null;
  job_title?: string | null;
  notes?: string | null;
  photo_url?: string | null;
  source: string;
  source_id?: string | null;
  last_synced_at?: string | null;
  editable: boolean;
  tags?: string[];
  whatsapp?: string | null;
  telegram?: string | null;
  role?: string | null;
};

export type ContactSearchResult = {
  id: string;
  display_name: string;
  organisation?: string | null;
  primary_email?: string | null;
  primary_phone?: string | null;
  score: number;
};

export type ContactPreferences = {
  user_id: string;
  confirm_before_email: boolean;
  confirm_before_call: boolean;
  read_back_draft: boolean;
};

export type SyncSource = {
  id: string;
  provider: string;
  display_name: string;
  last_full_sync_at?: string | null;
  last_delta_sync_at?: string | null;
  last_sync_error?: string | null;
  contact_count?: number;
  sync_enabled?: boolean;
  sync_interval_minutes?: number;
  carddav_url?: string;
};

export type ContactActivityItem = {
  id: string;
  kind: "email" | "meeting" | string;
  at?: string | null;
  title: string;
  subtitle?: string;
  href?: string;
  meta?: string;
};

export type ContactActivity = {
  items: ContactActivityItem[];
  counts: { email: number; meeting: number; total: number };
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return payload as T;
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const raw = search.toString();
  return raw ? `?${raw}` : "";
}

export async function fetchContacts(opts?: {
  q?: string;
  source?: string;
  limit?: number;
  offset?: number;
}): Promise<Contact[]> {
  return parseJson(
    await ceApi(
      `/api/contacts${qs({
        q: opts?.q,
        source: opts?.source && opts.source !== "all" ? opts.source : undefined,
        limit: opts?.limit ?? 100,
        offset: opts?.offset ?? 0,
      })}`,
    ),
    "Failed to load contacts",
  );
}

export async function fetchContact(id: string): Promise<Contact> {
  return parseJson(await ceApi(`/api/contacts/${encodeURIComponent(id)}`), "Contact not found");
}

export async function fetchContactActivity(id: string): Promise<ContactActivity> {
  return parseJson(
    await ceApi(`/api/contacts/${encodeURIComponent(id)}/activity`),
    "Failed to load activity",
  );
}

export async function searchContacts(q: string): Promise<ContactSearchResult[]> {
  return parseJson(
    await ceApi(`/api/contacts/search?q=${encodeURIComponent(q)}`),
    "Search failed",
  );
}

export async function createContact(body: Partial<Contact> & { display_name: string }): Promise<Contact> {
  return parseJson(
    await ceApi("/api/contacts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to create contact",
  );
}

export async function updateContact(id: string, body: Partial<Contact>): Promise<Contact> {
  return parseJson(
    await ceApi(`/api/contacts/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to update contact",
  );
}

export async function deleteContact(id: string): Promise<void> {
  const response = await ceApi(`/api/contacts/${encodeURIComponent(id)}`, { method: "DELETE" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Failed to delete contact"));
  }
}

export async function patchContactEnrichment(
  id: string,
  body: { tags?: string[]; whatsapp?: string | null; telegram?: string | null; role?: string | null },
): Promise<Contact> {
  return parseJson(
    await ceApi(`/api/contacts/${encodeURIComponent(id)}/enrichment`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to update contact enrichment",
  );
}

export function primaryEmail(contact: Contact): string | undefined {
  return contact.emails.find((e) => e.primary)?.address || contact.emails[0]?.address;
}

export function primaryPhone(contact: Contact): string | undefined {
  return contact.phones.find((p) => p.primary)?.number || contact.phones[0]?.number;
}

export function digitsForDial(phone?: string | null): string | null {
  const raw = String(phone ?? "").trim();
  if (!raw) return null;
  const cleaned = raw.replace(/[^\d+]/g, "");
  const digits = cleaned.replace(/\D+/g, "");
  if (digits.length < 7) return null;
  return cleaned.startsWith("+") ? `+${digits}` : digits;
}

export function whatsappHref(phone?: string | null): string | null {
  const dial = digitsForDial(phone);
  if (!dial) return null;
  return `https://wa.me/${dial.replace(/\D+/g, "")}`;
}

export async function fetchSyncSources(): Promise<SyncSource[]> {
  return parseJson(await ceApi("/api/contacts/sync/sources"), "Failed to load sync sources");
}

export async function createCardDavSource(body: {
  display_name: string;
  carddav_url: string;
  carddav_username: string;
  carddav_password: string;
  sync_interval_minutes?: number;
}): Promise<SyncSource & { initial_sync?: Record<string, unknown> }> {
  return parseJson(
    await ceApi("/api/contacts/sync/sources", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "CardDAV setup failed",
  );
}

export async function updateSyncSource(
  sourceId: string,
  body: { sync_enabled?: boolean; sync_interval_minutes?: number; display_name?: string },
): Promise<SyncSource> {
  return parseJson(
    await ceApi(`/api/contacts/sync/sources/${sourceId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to update sync source",
  );
}

export async function deleteSyncSource(sourceId: string): Promise<void> {
  const response = await ceApi(`/api/contacts/sync/sources/${sourceId}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Failed to remove sync source");
}

export async function triggerSync(sourceId: string): Promise<Record<string, unknown>> {
  return parseJson(await ceApi(`/api/contacts/sync/${sourceId}/now`, { method: "POST" }), "Sync failed");
}

export type GoogleOAuthConfig = {
  configured: boolean;
  source: string;
  client_id_masked: string;
  redirect_uri: string;
  people_api_hint?: string;
};

export async function fetchGoogleOAuthConfig(): Promise<GoogleOAuthConfig> {
  return parseJson(await ceApi("/api/contacts/sync/google/config"), "Failed to load Google OAuth config");
}

export async function saveGoogleOAuthConfig(body: {
  client_id: string;
  client_secret: string;
}): Promise<GoogleOAuthConfig> {
  return parseJson(
    await ceApi("/api/contacts/sync/google/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to save Google OAuth credentials",
  );
}

export async function clearGoogleOAuthConfig(): Promise<GoogleOAuthConfig> {
  return parseJson(await ceApi("/api/contacts/sync/google/config", { method: "DELETE" }), "Failed to clear Google OAuth credentials");
}

export async function fetchGoogleAuthUrl(): Promise<string> {
  const data = await parseJson<{ auth_url: string }>(
    await ceApi("/api/contacts/sync/google/auth"),
    "Google OAuth not configured",
  );
  return data.auth_url;
}

export async function fetchMicrosoftAuthUrl(): Promise<string> {
  const data = await parseJson<{ auth_url: string }>(
    await ceApi("/api/contacts/sync/microsoft/auth"),
    "Microsoft OAuth not configured",
  );
  return data.auth_url;
}

export async function fetchContactPreferences(): Promise<ContactPreferences> {
  return parseJson(await ceApi("/api/contacts/preferences"), "Failed to load preferences");
}

export async function updateContactPreferences(
  body: Partial<ContactPreferences>,
): Promise<ContactPreferences> {
  return parseJson(
    await ceApi("/api/contacts/preferences", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to update preferences",
  );
}

export async function importContactsFile(file: File, kind: "vcf" | "csv"): Promise<Record<string, number>> {
  const form = new FormData();
  form.append("file", file);
  const response = await ceApi(`/api/contacts/import/${kind}`, {
    method: "POST",
    body: form,
    headers: {},
  });
  if (!response.ok) throw new Error("Import failed");
  return response.json();
}
