import { buildApiHeaders, ceApi, getApiBaseUrl } from "@/lib/ce-api";

export type WorkspaceSession = {
  id: string;
  title: string;
  preview?: string;
  created_at?: string;
  updated_at?: string;
};

export type AvailableModel = {
  id: string;
  provider: string;
  name: string;
};

export type WorkspaceMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: MessageBlock[];
  createdAt: string;
};

export type MessageBlock =
  | { type: "text"; content: string }
  | { type: "thinking"; content: string }
  | {
      type: "tool_call";
      name: string;
      input: Record<string, unknown>;
      output?: string;
      status: "running" | "done" | "error";
      mode?: "dry_run" | "live";
    }
  | { type: "code"; language: string; content: string }
  | { type: "file"; path: string; action: "created" | "modified" | "deleted" }
  | {
      type: "mutation";
      id?: string;
      toolName: string;
      approach?: string;
      code: string;
      skillYaml: string;
      sandboxResult: string;
      sandboxExitCode?: number;
      sandboxStderr?: string;
      status: "pending" | "approved" | "rejected";
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

export type WorkspaceDocument = {
  id: string;
  title: string;
  content: string;
  format: string;
  tags: string[];
  word_count?: number;
  updated_at?: string;
  is_shared?: boolean;
  share_token?: string | null;
  is_favorite?: boolean;
  folder?: string;
};

export type WorkspaceNote = {
  id: string;
  title: string;
  content: string;
  tags: string[];
  is_pinned: boolean;
  updated_at?: string;
};

export type WorkspaceTask = {
  id: string;
  title: string;
  description: string;
  status: "todo" | "in_progress" | "done";
  priority: string;
  due_at?: string | null;
  tags: string[];
  agent_scheduled?: boolean;
  sort_order?: number;
};

export type CalendarEvent = {
  id: string;
  title: string;
  description: string;
  location: string;
  start_at: string;
  end_at: string;
  all_day: boolean;
  caldav_source_id?: string | null;
  external_readonly?: boolean;
  metadata?: Record<string, unknown> | null;
};

export type CalendarProviderPreset = {
  id: string;
  label: string;
  provider: string;
  sync_modes: string[];
  url_hint: string;
  help: string;
};

export type CalendarSource = {
  id: string;
  name: string;
  provider: string;
  url: string;
  username: string;
  has_password: boolean;
  sync_direction: string;
  calendar_href?: string | null;
  calendar_name?: string | null;
  push_local_events: boolean;
  enabled: boolean;
  auto_sync: boolean;
  sync_interval_minutes: number;
  pull_past_days: number;
  pull_future_days: number;
  last_sync_at?: string | null;
  last_sync_ok?: boolean | null;
  last_sync_message?: string | null;
  next_sync_at?: string | null;
  created_at?: string;
};

export type CalendarAutoSyncStatus = {
  enabled: boolean;
  running: boolean;
  tick_seconds: number;
  default_interval_minutes: number;
  min_interval_minutes: number;
  max_interval_minutes: number;
};

export type CalendarSyncResult = {
  ok: boolean;
  synced?: number;
  pulled?: number;
  pushed?: number;
  errors?: number;
  message?: string;
  results?: Array<Record<string, unknown>>;
};

export async function fetchDocuments(opts?: {
  q?: string;
  tag?: string;
  folder?: string;
  favorites?: boolean;
}): Promise<WorkspaceDocument[]> {
  const params = new URLSearchParams();
  if (opts?.q) params.set("q", opts.q);
  if (opts?.tag) params.set("tag", opts.tag);
  if (opts?.folder !== undefined) params.set("folder", opts.folder);
  if (opts?.favorites) params.set("favorites", "true");
  const suffix = params.toString() ? `?${params}` : "";
  const data = await parseJson<{ items: WorkspaceDocument[] }>(
    await ceApi(`/api/workspace/documents${suffix}`),
    "Failed to load documents",
  );
  return data.items;
}

export async function createDocument(body: {
  title: string;
  content: string;
  format?: string;
  tags?: string[];
  folder?: string;
}): Promise<WorkspaceDocument> {
  return parseJson(
    await ceApi("/api/workspace/documents", {
      method: "POST",
      body: JSON.stringify({ format: "markdown", ...body }),
    }),
    "Failed to create document",
  );
}

export async function updateDocument(
  id: string,
  body: Partial<Pick<WorkspaceDocument, "title" | "content" | "format" | "tags">>,
): Promise<WorkspaceDocument> {
  return parseJson(
    await ceApi(`/api/workspace/documents/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "Failed to update document",
  );
}

export async function patchDocumentMeta(
  id: string,
  body: { is_favorite?: boolean; folder?: string },
): Promise<WorkspaceDocument> {
  return parseJson(
    await ceApi(`/api/workspace/documents/${id}/meta`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
    "Failed to update document meta",
  );
}

export async function deleteDocument(id: string): Promise<void> {
  const response = await ceApi(`/api/workspace/documents/${id}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Failed to delete document");
  }
}

export async function exportDocument(id: string, format: "md" | "html" | "txt" | "pdf"): Promise<Blob> {
  const response = await ceApi(`/api/workspace/documents/${id}/export?format=${format}`);
  if (!response.ok) {
    throw new Error("Export failed");
  }
  return response.blob();
}

export async function shareDocument(id: string): Promise<{ share_token: string; path: string }> {
  return parseJson(
    await ceApi(`/api/workspace/documents/${id}/share`, { method: "POST" }),
    "Share failed",
  );
}

export async function aiEditDocument(id: string, instruction: string): Promise<{ content: string }> {
  return parseJson(
    await ceApi(`/api/workspace/documents/${id}/ai-edit`, {
      method: "POST",
      body: JSON.stringify({ instruction }),
    }),
    "AI edit failed",
  );
}

export async function aiSuggestDocument(id: string): Promise<{ suggestions: string[] }> {
  return parseJson(
    await ceApi(`/api/workspace/documents/${id}/ai-suggest`, { method: "POST" }),
    "AI suggest failed",
  );
}

export async function fetchDocumentVersions(
  id: string,
): Promise<Array<{ id: string; title: string; content: string; created_at: string }>> {
  const data = await parseJson<{
    items: Array<{ id: string; title: string; content: string; created_at: string }>;
  }>(await ceApi(`/api/workspace/documents/${id}/versions`), "Failed to load versions");
  return data.items;
}

export async function restoreDocumentVersion(docId: string, versionId: string): Promise<WorkspaceDocument> {
  return parseJson(
    await ceApi(`/api/workspace/documents/${docId}/versions/${versionId}/restore`, { method: "POST" }),
    "Restore failed",
  );
}

export async function importDocumentFile(file: File): Promise<WorkspaceDocument> {
  const form = new FormData();
  form.append("file", file);
  return parseJson(
    await ceApi("/api/workspace/documents/import", {
      method: "POST",
      body: form,
      headers: {},
    }),
    "Import failed",
  );
}

export async function importDocumentFromPath(path: string, folder = "disk"): Promise<WorkspaceDocument> {
  return parseJson(
    await ceApi("/api/workspace/documents/import-path", {
      method: "POST",
      body: JSON.stringify({ path, folder, tags: ["disk", "imported"] }),
    }),
    "Import from path failed",
  );
}

export async function fetchSharedDocument(token: string): Promise<WorkspaceDocument> {
  return parseJson(
    await ceApi(`/api/workspace/documents/shared/${encodeURIComponent(token)}`),
    "Shared document not found",
  );
}

export async function fetchNotes(search?: string): Promise<WorkspaceNote[]> {
  const path = search
    ? `/api/workspace/notes?search=${encodeURIComponent(search)}`
    : "/api/workspace/notes";
  const data = await parseJson<{ items: WorkspaceNote[] }>(await ceApi(path), "Failed to load notes");
  return data.items;
}

export async function createNote(body: {
  title: string;
  content: string;
  tags?: string[];
  is_pinned?: boolean;
}): Promise<WorkspaceNote> {
  return parseJson(
    await ceApi("/api/workspace/notes", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to create note",
  );
}

export async function updateNote(
  id: string,
  body: Partial<Pick<WorkspaceNote, "title" | "content" | "tags" | "is_pinned">>,
): Promise<WorkspaceNote> {
  return parseJson(
    await ceApi(`/api/workspace/notes/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "Failed to update note",
  );
}

export async function deleteNote(id: string): Promise<void> {
  const response = await ceApi(`/api/workspace/notes/${id}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Failed to delete note");
  }
}

export async function fetchTasks(status?: string): Promise<WorkspaceTask[]> {
  const path = status
    ? `/api/workspace/tasks?status=${encodeURIComponent(status)}`
    : "/api/workspace/tasks";
  const data = await parseJson<{ items: WorkspaceTask[] }>(await ceApi(path), "Failed to load tasks");
  return data.items;
}

export async function createTask(body: {
  title: string;
  description?: string;
  status?: string;
  priority?: string;
  due_at?: string | null;
  tags?: string[];
}): Promise<WorkspaceTask> {
  return parseJson(
    await ceApi("/api/workspace/tasks", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to create task",
  );
}

export async function updateTask(
  id: string,
  body: Partial<Pick<WorkspaceTask, "title" | "description" | "status" | "priority" | "due_at" | "tags">>,
): Promise<WorkspaceTask> {
  return parseJson(
    await ceApi(`/api/workspace/tasks/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
    "Failed to update task",
  );
}

export async function completeTask(id: string): Promise<WorkspaceTask> {
  return parseJson(
    await ceApi(`/api/workspace/tasks/${id}/complete`, { method: "POST" }),
    "Failed to complete task",
  );
}

export async function deleteTask(id: string): Promise<void> {
  const response = await ceApi(`/api/workspace/tasks/${id}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Failed to delete task");
  }
}

export async function reorderTasks(order: string[]): Promise<WorkspaceTask[]> {
  const data = await parseJson<{ items: WorkspaceTask[] }>(
    await ceApi("/api/workspace/tasks/reorder", {
      method: "POST",
      body: JSON.stringify({ order }),
    }),
    "Failed to reorder tasks",
  );
  return data.items;
}

export async function fetchCalendarEvents(start: string, end: string): Promise<CalendarEvent[]> {
  const params = new URLSearchParams({ start, end });
  const data = await parseJson<{ items: CalendarEvent[] }>(
    await ceApi(`/api/workspace/calendar/events?${params}`),
    "Failed to load calendar events",
  );
  return data.items;
}

export async function fetchCalendarEvent(eventId: string): Promise<CalendarEvent> {
  return parseJson(
    await ceApi(`/api/workspace/calendar/events/${encodeURIComponent(eventId)}`),
    "Failed to load calendar event",
  );
}

/** Booking id bridged onto a calendar event by viCal confirm. */
export function vicalBookingIdFromEvent(event: CalendarEvent): string | null {
  const meta = event.metadata;
  if (!meta || typeof meta !== "object") return null;
  const raw = meta.vical_booking_id ?? meta.booking_id;
  return typeof raw === "string" && raw.trim() ? raw.trim() : null;
}

export function contactIdFromEvent(event: CalendarEvent): string | null {
  const meta = event.metadata;
  if (!meta || typeof meta !== "object") return null;
  const raw = meta.contact_id;
  return typeof raw === "string" && raw.trim() ? raw.trim() : null;
}

export async function createCalendarEvent(body: {
  title: string;
  description?: string;
  start_at: string;
  end_at: string;
  all_day?: boolean;
}): Promise<CalendarEvent> {
  return parseJson(
    await ceApi("/api/workspace/calendar/events", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to create event",
  );
}

export async function fetchCalendarProviders(): Promise<CalendarProviderPreset[]> {
  const data = await parseJson<{ items: CalendarProviderPreset[] }>(
    await ceApi("/api/workspace/calendar/providers"),
    "Failed to load calendar providers",
  );
  return data.items;
}

export async function fetchCalendarSources(): Promise<CalendarSource[]> {
  const data = await parseJson<{ items: CalendarSource[] }>(
    await ceApi("/api/workspace/calendar/sources"),
    "Failed to load calendar sources",
  );
  return data.items;
}

export async function createCalendarSource(body: {
  name: string;
  provider: string;
  url?: string;
  username?: string;
  password?: string;
  sync_direction?: string;
  calendar_name?: string;
  push_local_events?: boolean;
  auto_sync?: boolean;
  sync_interval_minutes?: number;
  pull_past_days?: number;
  pull_future_days?: number;
}): Promise<CalendarSource> {
  return parseJson(
    await ceApi("/api/workspace/calendar/sources", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Failed to connect calendar",
  );
}

export async function updateCalendarSource(
  sourceId: string,
  body: {
    auto_sync?: boolean;
    sync_interval_minutes?: number;
    sync_direction?: string;
    push_local_events?: boolean;
    enabled?: boolean;
  },
): Promise<CalendarSource> {
  return parseJson(
    await ceApi(`/api/workspace/calendar/sources/${sourceId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
    "Failed to update calendar source",
  );
}

export async function fetchCalendarAutoSyncStatus(): Promise<CalendarAutoSyncStatus> {
  return parseJson(await ceApi("/api/workspace/calendar/auto-sync"), "Failed to load auto-sync status");
}

export async function deleteCalendarSource(sourceId: string, removeEvents = false): Promise<void> {
  const params = new URLSearchParams();
  if (removeEvents) params.set("remove_events", "true");
  const suffix = params.toString() ? `?${params}` : "";
  const response = await ceApi(`/api/workspace/calendar/sources/${sourceId}${suffix}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Failed to remove calendar source");
  }
}

export async function syncCalendarSources(): Promise<CalendarSyncResult> {
  return parseJson(await ceApi("/api/workspace/calendar/sync", { method: "POST" }), "Failed to sync calendars");
}

export async function syncCalendarSource(sourceId: string): Promise<CalendarSyncResult> {
  return parseJson(
    await ceApi(`/api/workspace/calendar/sources/${sourceId}/sync`, { method: "POST" }),
    "Failed to sync calendar source",
  );
}

export async function createConversation(title = "New conversation"): Promise<{ id: string }> {
  return parseJson(
    await ceApi("/api/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
    "create conversation",
  );
}

export async function fetchConversations(limit = 50): Promise<WorkspaceSession[]> {
  const data = await parseJson<{ items: WorkspaceSession[] }>(
    await ceApi(`/api/conversations?limit=${limit}&sort=created_at:desc`),
    "conversations",
  );
  return data.items;
}

export async function fetchConversation(sessionId: string): Promise<{ messages: WorkspaceMessage[]; title: string }> {
  const data = await parseJson<{ messages: WorkspaceMessage[]; title: string }>(
    await ceApi(`/api/conversations/${sessionId}`),
    "conversation",
  );
  return data;
}

export async function renameConversation(sessionId: string, title: string): Promise<void> {
  const response = await ceApi(`/api/conversations/${sessionId}`, {
    method: "PUT",
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    throw new Error("rename failed");
  }
}

export async function deleteConversation(sessionId: string): Promise<void> {
  const response = await ceApi(`/api/conversations/${sessionId}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("delete failed");
  }
}

export async function fetchAvailableModels(): Promise<AvailableModel[]> {
  const data = await parseJson<{ models?: AvailableModel[] } | AvailableModel[]>(
    await ceApi("/api/models/available"),
    "models",
  );
  if (Array.isArray(data)) {
    return data;
  }
  return Array.isArray(data.models) ? data.models : [];
}

export async function uploadChatFile(file: File): Promise<{ id: string; filename: string }> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${getApiBaseUrl()}/api/files/upload`, {
    method: "POST",
    headers: buildApiHeaders(),
    body: form,
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error("upload failed");
  }
  return response.json();
}

export async function openFileInEditor(path: string): Promise<void> {
  const response = await ceApi("/api/files/open", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
  if (!response.ok) {
    throw new Error("open failed");
  }
}

export type GeneratedToolRecord = {
  id: string;
  tool_name: string;
  status: string;
  task_that_triggered?: string;
  session_id?: string | null;
};

export type ApproveMutationResponse = {
  record: GeneratedToolRecord;
  retry_message?: string;
  message?: WorkspaceMessage;
  status?: string;
  tool_name?: string;
};

export async function approveMutation(id: string, sessionId?: string): Promise<ApproveMutationResponse> {
  const query = new URLSearchParams();
  if (sessionId) {
    query.set("session_id", sessionId);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const response = await ceApi(`/api/mutations/${id}/approve${suffix}`, { method: "POST" });
  if (!response.ok) {
    throw new Error("approve failed");
  }
  return response.json();
}

export async function rejectMutation(id: string, reason?: string): Promise<void> {
  const response = await ceApi(`/api/mutations/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) {
    throw new Error("reject failed");
  }
}

export function normalizeMessages(raw: unknown[]): WorkspaceMessage[] {
  return raw.map((item) => {
    const message = item as WorkspaceMessage & { content?: unknown };
    const content = Array.isArray(message.content)
      ? message.content
      : typeof message.content === "string"
        ? [{ type: "text" as const, content: message.content }]
        : [];
    return {
      id: message.id,
      role: message.role,
      content: content as MessageBlock[],
      createdAt: message.createdAt || new Date().toISOString(),
    };
  });
}
