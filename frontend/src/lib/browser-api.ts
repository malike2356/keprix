import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type BrowserProfile = {
  id: string;
  workspace_id: string;
  name: string;
  kind: string;
  vault_credential_id?: string | null;
  read_only?: boolean;
};

export type HarnessSession = {
  session_id: string;
  trace_id: string;
  workspace_id: string;
  objective: string;
  url: string;
  created_at?: string;
  mode?: "dry_run" | "live";
  step_count?: number;
  metadata?: Record<string, unknown>;
};

export type BrowserSessionStep = {
  id: string;
  session_id: string;
  action: string;
  selector: string;
  status: string;
  created_at: string;
  screenshot_id?: string | null;
  metadata?: Record<string, unknown>;
};

export type HarnessSnapshot = {
  session_id: string;
  trace_id: string;
  url: string;
  title: string;
  dom_snapshot: string;
  accessibility_tree: Array<Record<string, unknown>>;
  screenshot_id?: string | null;
  console_logs: Array<Record<string, unknown>>;
  network_summary: Array<Record<string, unknown>>;
  download_events: Array<Record<string, unknown>>;
  upload_controls: Array<Record<string, unknown>>;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(async () => {
      const text = await response.text().catch(() => "");
      return text ? { detail: text } : {};
    });
    if (response.status === 401) {
      throw new Error(
        parseApiErrorMessage(payload, "Sign in required to load browser sessions"),
      );
    }
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
}

export async function fetchBrowserProfiles(workspaceId = "default") {
  return parseJson<{ profiles: BrowserProfile[] }>(
    await ceApi(`/api/browser/profiles?workspace_id=${encodeURIComponent(workspaceId)}`),
    "browser profiles",
  );
}

export async function createBrowserProfile(body: {
  workspace_id?: string;
  name: string;
  kind: string;
  vault_credential_id?: string;
}) {
  return parseJson<BrowserProfile>(
    await ceApi("/api/browser/profiles", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "create browser profile",
  );
}

export async function openHarnessSession(body: {
  workspace_id?: string;
  objective: string;
  url?: string;
  profile_id?: string;
}) {
  return parseJson<{ session_id: string; trace_id: string; snapshot: HarnessSnapshot }>(
    await ceApi("/api/browser/harness/session", {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "open harness session",
  );
}

export async function fetchHarnessSessions(workspaceId = "default") {
  return parseJson<{ sessions: HarnessSession[] }>(
    await ceApi(`/api/browser/harness/sessions?workspace_id=${encodeURIComponent(workspaceId)}`),
    "harness sessions",
  );
}

export async function fetchHarnessSnapshot(sessionId: string) {
  return parseJson<HarnessSnapshot>(
    await ceApi(`/api/browser/harness/${encodeURIComponent(sessionId)}/snapshot`),
    "harness snapshot",
  );
}

export async function fetchBrowserSkills() {
  return parseJson<{ skills: Array<{ name: string; description: string; risk: string; approval_required: boolean }> }>(
    await ceApi("/api/browser/skills"),
    "browser skills",
  );
}

export async function fetchBrowserSessions(workspaceId = "default") {
  return parseJson<{ sessions: HarnessSession[] }>(
    await ceApi(`/api/browser/sessions?workspace_id=${encodeURIComponent(workspaceId)}`),
    "browser sessions",
  );
}

export async function fetchBrowserSessionSteps(sessionId: string) {
  return parseJson<{ session_id: string; mode: string; steps: BrowserSessionStep[] }>(
    await ceApi(`/api/browser/sessions/${encodeURIComponent(sessionId)}/steps`),
    "browser session steps",
  );
}
