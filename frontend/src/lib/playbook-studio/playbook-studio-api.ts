import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";
import type {
  StudioCanvas,
  StudioCompileError,
  StudioLoadResponse,
  StudioPlaybookSummary,
} from "@/lib/playbook-studio/canvas-types";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const errors = (payload as { compile_errors?: StudioCompileError[] }).compile_errors;
    const error = new Error(parseApiErrorMessage(payload, fallback)) as Error & {
      compile_errors?: StudioCompileError[];
    };
    error.compile_errors = errors;
    throw error;
  }
  return payload as T;
}

export async function listStudioPlaybooks(): Promise<StudioPlaybookSummary[]> {
  const data = await parseJson<{ playbooks: StudioPlaybookSummary[] }>(
    await ceApi("/api/playbooks/studio"),
    "Failed to load playbooks",
  );
  return data.playbooks || [];
}

export async function loadStudioPlaybook(id: string): Promise<StudioLoadResponse> {
  return parseJson<StudioLoadResponse>(
    await ceApi(`/api/playbooks/studio/${encodeURIComponent(id)}`),
    "Failed to load playbook",
  );
}

export async function saveStudioCanvas(id: string, canvas: StudioCanvas): Promise<void> {
  await parseJson(
    await ceApi(`/api/playbooks/studio/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify({ canvas }),
    }),
    "Failed to save playbook",
  );
}

export async function compileStudioCanvas(canvas: StudioCanvas): Promise<{
  yaml: Record<string, unknown>;
  errors: StudioCompileError[];
}> {
  return parseJson(
    await ceApi("/api/playbooks/studio/compile", {
      method: "POST",
      body: JSON.stringify({ canvas }),
    }),
    "Failed to compile playbook",
  );
}

export async function decompileStudioYaml(yaml: string): Promise<{ canvas: StudioCanvas }> {
  return parseJson(
    await ceApi("/api/playbooks/studio/decompile", {
      method: "POST",
      body: JSON.stringify({ yaml }),
    }),
    "Failed to open playbook in Studio",
  );
}

export async function publishStudioPlaybook(
  id: string,
  options?: { scope?: "personal" | "org"; note?: string; require_scout_approval?: boolean },
): Promise<{
  version_hash: string;
  status: string;
  scout_event_id?: string | null;
}> {
  return parseJson(
    await ceApi(`/api/playbooks/studio/${encodeURIComponent(id)}/publish`, {
      method: "POST",
      body: JSON.stringify(options || {}),
    }),
    "Failed to publish playbook",
  );
}

export type StudioVersion = {
  playbook_id: string;
  version_hash: string;
  published_at: string;
  publisher_user_id: string;
  scope: "personal" | "org";
  status: "draft" | "pending_approval" | "published" | "rejected";
  note?: string;
  scout_event_id?: string | null;
};

export async function listStudioVersions(id: string): Promise<StudioVersion[]> {
  const data = await parseJson<{ versions: StudioVersion[] }>(
    await ceApi(`/api/playbooks/studio/${encodeURIComponent(id)}/versions`),
    "Failed to load versions",
  );
  return data.versions || [];
}

export type StudioTemplate = {
  id: string;
  title: string;
  description: string;
  source: string;
  yaml: Record<string, unknown>;
};

export async function listStudioTemplates(): Promise<StudioTemplate[]> {
  const data = await parseJson<{ templates: StudioTemplate[] }>(
    await ceApi("/api/playbooks/studio/templates"),
    "Failed to load templates",
  );
  return data.templates || [];
}

export async function loadStudioTemplate(id: string): Promise<{ template: StudioTemplate; canvas: StudioCanvas }> {
  return parseJson(
    await ceApi(`/api/playbooks/studio/templates/${encodeURIComponent(id)}`),
    "Failed to load template",
  );
}

export async function saveStudioTemplate(id: string, title: string, description: string): Promise<{ template_id: string }> {
  return parseJson(
    await ceApi(`/api/playbooks/studio/templates/from/${encodeURIComponent(id)}`, {
      method: "POST",
      body: JSON.stringify({ title, description }),
    }),
    "Failed to save template",
  );
}

export type CoachSuggestion = {
  node_type: string;
  label: string;
  reason: string;
  prefilled_data: Record<string, unknown>;
};

export async function fetchCoachSuggestions(canvas: StudioCanvas, selected_node_id: string | null): Promise<CoachSuggestion[]> {
  const data = await parseJson<{ suggestions: CoachSuggestion[] }>(
    await ceApi("/api/playbooks/studio/coach", {
      method: "POST",
      body: JSON.stringify({ canvas, selected_node_id }),
    }),
    "Failed to load coach suggestions",
  );
  return data.suggestions || [];
}

export async function importN8nWorkflow(workflow: Record<string, unknown>): Promise<{
  canvas: StudioCanvas;
  warnings: string[];
  suggested_id: string;
}> {
  return parseJson(
    await ceApi("/api/playbooks/studio/import/n8n", {
      method: "POST",
      body: JSON.stringify({ workflow }),
    }),
    "Failed to import n8n workflow",
  );
}

export async function importYamlPlaybook(yaml: string): Promise<{ canvas: StudioCanvas; playbook_id: string }> {
  return parseJson(
    await ceApi("/api/playbooks/studio/import/yaml", {
      method: "POST",
      body: JSON.stringify({ yaml }),
    }),
    "Failed to import YAML",
  );
}

export function studioExportUrl(id: string): string {
  return `/api/playbooks/studio/${encodeURIComponent(id)}/export`;
}
