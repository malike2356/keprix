import { ceApi } from "@/lib/ce-api";

export type Contact = {
  id: string;
  display_name: string;
  given_name?: string | null;
  family_name?: string | null;
  emails: Array<{ address: string; label?: string; primary?: boolean }>;
  phones: Array<{ number: string; label?: string; primary?: boolean }>;
  organisation?: string | null;
  job_title?: string | null;
  notes?: string | null;
  source: string;
  editable: boolean;
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

export async function fetchContacts(q?: string): Promise<Contact[]> {
  const path = q ? `/api/contacts?q=${encodeURIComponent(q)}` : "/api/contacts";
  const response = await ceApi(path);
  if (!response.ok) {
    throw new Error("Failed to load contacts");
  }
  return response.json();
}

export async function searchContacts(q: string): Promise<ContactSearchResult[]> {
  const response = await ceApi(`/api/contacts/search?q=${encodeURIComponent(q)}`);
  if (!response.ok) {
    throw new Error("Search failed");
  }
  return response.json();
}

export async function createContact(body: Partial<Contact>): Promise<Contact> {
  const response = await ceApi("/api/contacts", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error("Failed to create contact");
  }
  return response.json();
}

export async function fetchSyncSources(): Promise<SyncSource[]> {
  const response = await ceApi("/api/contacts/sync/sources");
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(
      (payload as { detail?: string }).detail || "Failed to load sync sources",
    );
  }
  return response.json();
}

export async function createCardDavSource(body: {
  display_name: string;
  carddav_url: string;
  carddav_username: string;
  carddav_password: string;
  sync_interval_minutes?: number;
}): Promise<SyncSource & { initial_sync?: Record<string, unknown> }> {
  const response = await ceApi("/api/contacts/sync/sources", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(
      (payload as { detail?: string }).detail || "CardDAV setup failed",
    );
  }
  return response.json();
}

export async function updateSyncSource(
  sourceId: string,
  body: { sync_enabled?: boolean; sync_interval_minutes?: number; display_name?: string },
): Promise<SyncSource> {
  const response = await ceApi(`/api/contacts/sync/sources/${sourceId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(
      (payload as { detail?: string }).detail || "Failed to update sync source",
    );
  }
  return response.json();
}

export async function deleteSyncSource(sourceId: string): Promise<void> {
  const response = await ceApi(`/api/contacts/sync/sources/${sourceId}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Failed to remove sync source");
  }
}

export async function triggerSync(sourceId: string): Promise<Record<string, unknown>> {
  const response = await ceApi(`/api/contacts/sync/${sourceId}/now`, { method: "POST" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { detail?: string }).detail || "Sync failed");
  }
  return response.json();
}

export type GoogleOAuthConfig = {
  configured: boolean;
  source: string;
  client_id_masked: string;
  redirect_uri: string;
  people_api_hint?: string;
};

export async function fetchGoogleOAuthConfig(): Promise<GoogleOAuthConfig> {
  const response = await ceApi("/api/contacts/sync/google/config");
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(
      (payload as { detail?: string }).detail || "Failed to load Google OAuth config",
    );
  }
  return response.json();
}

export async function saveGoogleOAuthConfig(body: {
  client_id: string;
  client_secret: string;
}): Promise<GoogleOAuthConfig> {
  const response = await ceApi("/api/contacts/sync/google/config", {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(
      (payload as { detail?: string }).detail || "Failed to save Google OAuth credentials",
    );
  }
  return response.json();
}

export async function clearGoogleOAuthConfig(): Promise<GoogleOAuthConfig> {
  const response = await ceApi("/api/contacts/sync/google/config", { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Failed to clear Google OAuth credentials");
  }
  return response.json();
}

export async function fetchGoogleAuthUrl(): Promise<string> {
  const response = await ceApi("/api/contacts/sync/google/auth");
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(
      (payload as { detail?: string }).detail || "Google OAuth not configured",
    );
  }
  const data = (await response.json()) as { auth_url: string };
  return data.auth_url;
}

export async function fetchMicrosoftAuthUrl(): Promise<string> {
  const response = await ceApi("/api/contacts/sync/microsoft/auth");
  if (!response.ok) {
    throw new Error("Microsoft OAuth not configured");
  }
  const data = (await response.json()) as { auth_url: string };
  return data.auth_url;
}

export async function fetchContactPreferences(): Promise<ContactPreferences> {
  const response = await ceApi("/api/contacts/preferences");
  if (!response.ok) {
    throw new Error("Failed to load preferences");
  }
  return response.json();
}

export async function updateContactPreferences(
  body: Partial<ContactPreferences>,
): Promise<ContactPreferences> {
  const response = await ceApi("/api/contacts/preferences", {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error("Failed to update preferences");
  }
  return response.json();
}

export async function importContactsFile(file: File, kind: "vcf" | "csv"): Promise<Record<string, number>> {
  const form = new FormData();
  form.append("file", file);
  const response = await ceApi(`/api/contacts/import/${kind}`, {
    method: "POST",
    body: form,
    headers: {},
  });
  if (!response.ok) {
    throw new Error("Import failed");
  }
  return response.json();
}
