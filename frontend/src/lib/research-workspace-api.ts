import { buildApiHeaders, ceApi, getApiBaseUrl, parseApiErrorMessage } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    let message = fallback;
    try {
      const payload = await response.json();
      message = parseApiErrorMessage(payload, fallback);
    } catch {
      const text = await response.text();
      if (text) message = text;
    }
    throw new Error(message);
  }
  return response.json();
}

function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export type ResearchProject = {
  project_id: string;
  title: string;
  question?: string | null;
  status?: string;
  owner?: string;
  trace_id?: string;
  sensitivity_level?: string;
  export_policy?: string;
};

export type ResearchBoundary = {
  keprix_owns: string[];
  external_tools: string[];
  references: Record<string, string>;
  note: string;
};

export async function fetchResearchBoundary() {
  return parseJson<ResearchBoundary>(
    await ceApi("/api/research/projects/boundary"),
    "research boundary",
  );
}

export async function fetchResearchProjects() {
  return parseJson<{ items: ResearchProject[] }>(
    await ceApi("/api/research/projects"),
    "research projects",
  );
}

export async function createResearchProject(payload: {
  title: string;
  question?: string;
  sensitivity_level?: string;
  export_policy?: string;
}) {
  return parseJson<{ project: ResearchProject }>(
    await ceApi("/api/research/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "create research project",
  );
}

export async function fetchResearchProject(projectId: string) {
  return parseJson<{ project: ResearchProject; objects: Array<Record<string, unknown>> }>(
    await ceApi(`/api/research/projects/${encodeURIComponent(projectId)}`),
    "research project",
  );
}

export async function addResearchSource(
  projectId: string,
  payload: { kind: string; ref: string; metadata?: Record<string, unknown> },
) {
  return parseJson<{ source: Record<string, unknown> }>(
    await ceApi(`/api/research/projects/${encodeURIComponent(projectId)}/sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "research source",
  );
}

export async function startResearchAnalysisRun(
  projectId: string,
  payload: { tool: string; parameters?: Record<string, unknown>; dataset_id?: string },
) {
  return parseJson<{ analysis_run: Record<string, unknown> }>(
    await ceApi(`/api/research/projects/${encodeURIComponent(projectId)}/analysis-runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "analysis run",
  );
}

export async function sendAnalyticsToResearchProject(
  projectId: string,
  payload: {
    title?: string;
    summary: string;
    chart_export?: Array<Record<string, unknown>> | Record<string, unknown>;
    analytics_session_id?: string | null;
  },
) {
  return parseJson<{ artifact: Record<string, unknown> }>(
    await ceApi(`/api/research/projects/${encodeURIComponent(projectId)}/artifacts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "analytics handoff",
  );
}

export async function exportResearchObsidian(projectId: string) {
  return parseJson<{ path: string; files: number }>(
    await ceApi(`/api/research/projects/${encodeURIComponent(projectId)}/export/obsidian`, {
      method: "POST",
    }),
    "obsidian export",
  );
}

export type ObsidianVault = {
  vault_id: string;
  name: string;
  local_path: string;
  sync_mode: string;
  allowed_folders?: string[];
  excluded_folders?: string[];
};

export type ObsidianIndexedNote = {
  path: string;
  title: string;
  tags?: string[];
  wikilinks?: string[];
  backlinks?: string[];
  meta?: Record<string, unknown>;
};

export async function listObsidianVaults() {
  return parseJson<{ items: ObsidianVault[] }>(
    await ceApi("/api/research/obsidian/vaults"),
    "obsidian vaults",
  );
}

export async function registerObsidianVault(payload: {
  name: string;
  local_path: string;
  sync_mode?: string;
  allow_external_path?: boolean;
  allowed_folders?: string[];
  excluded_folders?: string[];
}) {
  return parseJson<{ vault: ObsidianVault }>(
    await ceApi("/api/research/obsidian/vaults", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "register obsidian vault",
  );
}

export async function indexObsidianVault(vaultId: string) {
  return parseJson<{ note_count: number; notes: ObsidianIndexedNote[] }>(
    await ceApi(`/api/research/obsidian/vaults/${encodeURIComponent(vaultId)}/index`, {
      method: "POST",
    }),
    "index obsidian vault",
  );
}

export async function createObsidianDraftNote(
  projectId: string,
  payload: {
    vault_id: string;
    note_type: string;
    title: string;
    body?: string;
    source_id?: string;
    backlinks?: string[];
  },
) {
  return parseJson<{ note: { path: string }; note_type: string }>(
    await ceApi(`/api/research/obsidian/projects/${encodeURIComponent(projectId)}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "create obsidian draft note",
  );
}

export async function fetchObsidianBacklinks(projectId: string, vaultId: string) {
  return parseJson<{ items: ObsidianIndexedNote[]; backlink_index: Record<string, string[]> }>(
    await ceApi(
      `/api/research/obsidian/projects/${encodeURIComponent(projectId)}/backlinks?vault_id=${encodeURIComponent(vaultId)}`,
    ),
    "obsidian backlinks",
  );
}

export type ZoteroSettings = {
  mode: string;
  library_id?: string | null;
  library_type?: string;
  connected?: boolean;
  upload_attachments?: boolean;
};

export type CitationRecord = {
  item_key: string;
  citation_key: string;
  title: string;
  authors?: string[];
  year?: string | null;
  publication?: string | null;
  doi?: string | null;
  url?: string | null;
  abstract?: string | null;
  tags?: string[];
  source?: string;
  obsidian_note_path?: string | null;
};

export async function fetchZoteroSettings() {
  return parseJson<{ settings: ZoteroSettings }>(
    await ceApi("/api/research/zotero/settings"),
    "zotero settings",
  );
}

export async function connectZotero(payload: {
  mode: "web" | "local" | "file";
  api_key?: string;
  library_id?: string;
  library_type?: string;
  local_base_url?: string;
  upload_attachments?: boolean;
  obsidian_vault_id?: string;
}) {
  return parseJson<{ settings: ZoteroSettings }>(
    await ceApi("/api/research/zotero/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "connect zotero",
  );
}

export async function importZoteroBibTeX(payload: {
  project_id: string;
  content: string;
  format?: "bibtex" | "better-bibtex";
}) {
  return parseJson<{ imported: number; items: CitationRecord[] }>(
    await ceApi("/api/research/zotero/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "import zotero bibtex",
  );
}

export async function fetchProjectCitations(projectId: string) {
  return parseJson<{ items: CitationRecord[] }>(
    await ceApi(`/api/research/zotero/projects/${encodeURIComponent(projectId)}/citations`),
    "project citations",
  );
}

export async function createZoteroLiteratureNotes(
  projectId: string,
  payload: { citation_keys?: string[]; vault_id?: string; sections?: Record<string, string> },
) {
  return parseJson<{ notes: Array<Record<string, unknown>> }>(
    await ceApi(`/api/research/zotero/projects/${encodeURIComponent(projectId)}/literature-notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "zotero literature notes",
  );
}

export async function exportZoteroBibliography(
  projectId: string,
  payload: { format?: "bibtex" | "csl-json" | "markdown" | "report"; citation_keys?: string[] },
) {
  return parseJson<{ format: string; content: string; count: number }>(
    await ceApi(`/api/research/zotero/projects/${encodeURIComponent(projectId)}/bibliography`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "zotero bibliography",
  );
}

export async function importResearchDataset(projectId: string, name: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  const response = await ceApi(
    `/api/research/datasets/projects/${encodeURIComponent(projectId)}/import?name=${encodeURIComponent(name)}`,
    {
      method: "POST",
      body: form,
    },
  );
  return parseJson<{
    dataset_id: string;
    codebook: { variables: Array<Record<string, unknown>> };
  }>(response, "import dataset");
}

export async function fetchResearchDataset(datasetId: string) {
  return parseJson<{ dataset_id: string; codebook: Record<string, unknown>; lineage: Record<string, unknown> }>(
    await ceApi(`/api/research/datasets/${encodeURIComponent(datasetId)}`),
    "research dataset",
  );
}

export async function previewResearchDataset(datasetId: string) {
  return parseJson<{ columns: string[]; rows: Array<Record<string, unknown>> }>(
    await ceApi(`/api/research/datasets/${encodeURIComponent(datasetId)}/preview`),
    "dataset preview",
  );
}

export async function updateResearchCodebook(datasetId: string, codebook: Record<string, unknown>) {
  return parseJson<{ codebook: Record<string, unknown> }>(
    await ceApi(`/api/research/datasets/${encodeURIComponent(datasetId)}/codebook`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ codebook }),
    }),
    "update codebook",
  );
}

export async function exportResearchDataset(datasetId: string, format: string) {
  return parseJson<{ format: string; path?: string; notes_path?: string }>(
    await ceApi(`/api/research/datasets/${encodeURIComponent(datasetId)}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format }),
    }),
    "export dataset",
  );
}

export type PsppStatus = {
  installed: boolean;
  binary?: string | null;
  version?: string | null;
  setup_instructions?: string;
};

export type PsppGenerateResult = {
  run_id: string;
  trace_id: string;
  syntax_path: string;
};

export type PsppRunResult = {
  run_id: string;
  installed: boolean;
  status: string;
  setup_instructions?: string;
  syntax_path?: string;
  output_path?: string | null;
  stdout?: string;
  stderr?: string;
  parsed_tables?: Array<Record<string, unknown>>;
  warnings?: string[];
};

export async function fetchPsppStatus() {
  return parseJson<PsppStatus>(await ceApi("/api/research/pspp/status"), "PSPP status");
}

export async function generatePsppAnalysis(
  datasetId: string,
  procedures?: Array<Record<string, unknown>>,
) {
  return parseJson<PsppGenerateResult>(
    await ceApi("/api/research/pspp/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset_id: datasetId, procedures: procedures || [] }),
    }),
    "generate PSPP analysis",
  );
}

export async function runPsppAnalysis(runId: string, outputFormat: "txt" | "html" | "odt" = "txt") {
  return parseJson<PsppRunResult>(
    await ceApi("/api/research/pspp/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: runId, output_format: outputFormat }),
    }),
    "run PSPP analysis",
  );
}

export async function downloadResearchDatasetExport(
  datasetId: string,
  format: "jamovi" | "pspp" | "csv",
): Promise<void> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/research/datasets/${encodeURIComponent(datasetId)}/export/download?format=${encodeURIComponent(format)}`,
    {
      headers: buildApiHeaders(),
      credentials: "include",
    },
  );
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Download failed"));
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const defaults: Record<string, string> = {
    jamovi: `${datasetId}-jamovi.zip`,
    pspp: `${datasetId}.sps`,
    csv: `${datasetId}-clean.csv`,
  };
  triggerBrowserDownload(blob, match?.[1] || defaults[format]);
}

export type ResearchPlaybookSpec = {
  id: string;
  name: string;
  description: string;
  domain: string;
  step_count: number;
};

export type ResearchPlaybookRun = {
  trace_id: string;
  run: {
    run_id: string;
    playbook_id: string;
    playbook_name: string;
    status: string;
    dry_run: boolean;
    steps: Array<Record<string, unknown>>;
    pending_approvals: string[];
  };
};

export async function fetchResearchPlaybooks() {
  return parseJson<{ items: ResearchPlaybookSpec[] }>(
    await ceApi("/api/research/playbooks"),
    "research playbooks",
  );
}

export async function fetchResearchPlaybook(playbookId: string) {
  return parseJson<{ playbook: Record<string, unknown> }>(
    await ceApi(`/api/research/playbooks/${encodeURIComponent(playbookId)}`),
    "research playbook",
  );
}

export async function runResearchPlaybook(
  playbookId: string,
  payload: { project_id: string; dry_run?: boolean; parameters?: Record<string, unknown> },
) {
  return parseJson<ResearchPlaybookRun>(
    await ceApi(`/api/research/playbooks/${encodeURIComponent(playbookId)}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "run research playbook",
  );
}

export async function fetchResearchPlaybookRuns(projectId: string) {
  return parseJson<{ items: Array<Record<string, unknown>> }>(
    await ceApi(`/api/research/playbooks/projects/${encodeURIComponent(projectId)}/runs`),
    "research playbook runs",
  );
}
