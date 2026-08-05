import { buildApiHeaders, ceApi, getApiBaseUrl, parseApiErrorMessage } from "@/lib/ce-api";

export type AnalyticsSession = {
  session_id: string;
  title?: string;
  created_at?: string;
  code_history?: string[];
  variables?: Record<string, unknown>;
  artifacts?: string[];
  charts?: string[];
};

export type AnalyticsDataset = {
  dataset_id: string;
  name: string;
  data?: string;
  source_filename?: string | null;
  created_at?: string;
  chars?: number;
};

export type AnalyticsRunResult = {
  ok: boolean;
  verification_passed?: boolean;
  stdout?: string;
  stderr?: string;
  trail?: Array<Record<string, unknown>>;
};

export type AnalyticsFileParseResult = {
  filename: string;
  source_type: string;
  data: string;
  tabular: boolean;
  row_count: number;
  message?: string | null;
};

export async function parseAnalyticsFile(file: File): Promise<AnalyticsFileParseResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${getApiBaseUrl()}/api/analytics/parse-file`, {
    method: "POST",
    headers: buildApiHeaders(),
    body: form,
    credentials: "include",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Could not import file"));
  }
  return response.json();
}

export async function createAnalyticsSession(title?: string): Promise<AnalyticsSession> {
  const response = await ceApi("/api/analytics/sessions", {
    method: "POST",
    body: JSON.stringify({ title: title || null }),
  });
  if (!response.ok) throw new Error("Failed to create analytics session");
  return response.json();
}

export async function renameAnalyticsSession(sessionId: string, title: string): Promise<AnalyticsSession> {
  const response = await ceApi(`/api/analytics/sessions/${encodeURIComponent(sessionId)}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
  if (!response.ok) throw new Error("Failed to rename analytics session");
  return response.json();
}

export async function listAnalyticsDatasets(): Promise<{ datasets: AnalyticsDataset[] }> {
  const response = await ceApi("/api/analytics/datasets");
  if (!response.ok) throw new Error("Failed to list datasets");
  return response.json();
}

export async function saveAnalyticsDataset(body: {
  name: string;
  data: string;
  source_filename?: string;
}): Promise<AnalyticsDataset> {
  const response = await ceApi("/api/analytics/datasets", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Failed to save dataset");
  return response.json();
}

export async function fetchAnalyticsDataset(datasetId: string): Promise<AnalyticsDataset> {
  const response = await ceApi(`/api/analytics/datasets/${encodeURIComponent(datasetId)}`);
  if (!response.ok) throw new Error("Failed to load dataset");
  return response.json();
}

export async function deleteAnalyticsDataset(datasetId: string): Promise<void> {
  const response = await ceApi(`/api/analytics/datasets/${encodeURIComponent(datasetId)}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error("Failed to delete dataset");
}

export async function runAnalyticsCode(
  sessionId: string,
  code: string,
  autoRepair = true,
): Promise<AnalyticsRunResult> {
  const response = await ceApi(`/api/analytics/sessions/${sessionId}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, auto_repair: autoRepair }),
  });
  if (!response.ok) throw new Error("Analytics run failed");
  return response.json();
}

export async function fetchAnalyticsSession(sessionId: string): Promise<AnalyticsSession> {
  const response = await ceApi(`/api/analytics/sessions/${sessionId}`);
  if (!response.ok) throw new Error("Failed to load analytics session");
  return response.json();
}

export type AnalyticsSessionSummary = AnalyticsSession & {
  created_at?: string;
  code_runs?: number;
  code_history?: string[];
};

export async function fetchAnalyticsSessions(): Promise<{ sessions: AnalyticsSessionSummary[] }> {
  const response = await ceApi("/api/analytics/sessions");
  if (!response.ok) throw new Error("Failed to load analytics sessions");
  return response.json();
}

export async function fetchAnalyticsArtifacts(sessionId: string): Promise<{ artifacts: string[]; charts: string[] }> {
  const response = await ceApi(`/api/analytics/sessions/${sessionId}/artifacts`);
  if (!response.ok) throw new Error("Failed to load artifacts");
  return response.json();
}

export async function exportJamoviPackage(rows: Array<Record<string, unknown>>, datasetName = "analytics-export") {
  const response = await ceApi("/api/analytics/jamovi/export", {
    method: "POST",
    body: JSON.stringify({ rows, dataset_name: datasetName }),
  });
  if (!response.ok) throw new Error("Jamovi export failed");
  return response.json();
}

export function parseCsvToRows(data: string): Array<Record<string, unknown>> {
  const rows = parseCsvRows(data);
  if (rows.length < 2) {
    if (rows.length === 1) {
      throw new Error("CSV needs a header row and at least one data row.");
    }
    return [];
  }
  const headers = rows[0].map((cell) => cell.trim());
  if (headers.some((header) => !header)) {
    throw new Error("CSV header has an empty column name.");
  }
  return rows.slice(1).map((cells) => {
    const row: Record<string, unknown> = {};
    headers.forEach((header, index) => {
      row[header] = (cells[index] ?? "").trim();
    });
    return row;
  });
}

/** RFC4180-ish CSV splitter that respects quoted commas. */
export function parseCsvRows(data: string): string[][] {
  const text = data.replace(/^\uFEFF/, "");
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (inQuotes) {
      if (ch === '"' && next === '"') {
        cell += '"';
        i += 1;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        cell += ch;
      }
      continue;
    }
    if (ch === '"') {
      inQuotes = true;
      continue;
    }
    if (ch === ",") {
      row.push(cell);
      cell = "";
      continue;
    }
    if (ch === "\n") {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
      continue;
    }
    if (ch === "\r") {
      continue;
    }
    cell += ch;
  }
  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }
  return rows.filter((entry) => entry.some((value) => value.trim().length > 0));
}

function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function downloadJamoviPackage(
  rows: Array<Record<string, unknown>>,
  datasetName = "analytics-export",
): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/api/analytics/jamovi/export/download`, {
    method: "POST",
    headers: {
      ...buildApiHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ rows, dataset_name: datasetName }),
    credentials: "include",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Could not download jamovi package"));
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  triggerBrowserDownload(blob, match?.[1] || `${datasetName}-jamovi.zip`);
}
