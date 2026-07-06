import { buildApiHeaders, ceApi, getApiBaseUrl, parseApiErrorMessage } from "@/lib/ce-api";

export type AnalyticsSession = {
  session_id: string;
  created_at?: string;
  code_history?: string[];
  variables?: Record<string, unknown>;
  artifacts?: string[];
  charts?: string[];
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

export async function createAnalyticsSession(): Promise<AnalyticsSession> {
  const response = await ceApi("/api/analytics/sessions", { method: "POST" });
  if (!response.ok) throw new Error("Failed to create analytics session");
  return response.json();
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
  const lines = data.trim().split(/\r?\n/).filter((line) => line.trim());
  if (lines.length < 2) {
    return [];
  }
  const headers = lines[0].split(",").map((cell) => cell.trim());
  return lines.slice(1).map((line) => {
    const cells = line.split(",").map((cell) => cell.trim());
    const row: Record<string, unknown> = {};
    headers.forEach((header, index) => {
      row[header] = cells[index] ?? "";
    });
    return row;
  });
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
