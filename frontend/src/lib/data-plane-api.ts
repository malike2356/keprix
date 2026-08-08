import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type DataPlaneDataset = {
  id: string;
  name: string;
  format: string;
  path?: string;
  db_path?: string | null;
  engine?: string | null;
  row_count?: number | null;
  created_at?: string;
  updated_at?: string;
};

export type DataPlaneVersion = {
  version_id: string;
  dataset_id: string;
  version_number: number;
  path?: string;
  row_count?: number | null;
  lineage?: Record<string, unknown>;
  created_at?: string;
};

export type DataPlaneStatus = {
  control_plane?: Record<string, unknown>;
  data_plane?: Record<string, unknown>;
  retrieval_plane?: Record<string, unknown>;
  research_plane?: Record<string, unknown>;
  [key: string]: unknown;
};

export type DataQueryResult = {
  columns: string[];
  rows: Record<string, unknown>[];
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
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

export async function fetchDataPlanesStatus() {
  return parseJson<DataPlaneStatus>(
    await ceApi("/api/data/planes/status"),
    "Failed to load data plane status",
  );
}

export async function fetchDataCatalog() {
  return parseJson<{
    control_plane?: Record<string, unknown>;
    datasets: DataPlaneDataset[];
  }>(await ceApi("/api/data/catalog"), "Failed to load data catalog");
}

export async function fetchDataImportFormats() {
  return parseJson<{ formats: string[] }>(
    await ceApi("/api/data/import/formats"),
    "Failed to load import formats",
  );
}

export async function importDataDataset(file: File, name?: string) {
  const form = new FormData();
  form.append("file", file);
  return parseJson<{ dataset: DataPlaneDataset }>(
    await ceApi(`/api/data/datasets/import${qs({ name: name || file.name })}`, {
      method: "POST",
      body: form,
    }),
    "Failed to import dataset",
  );
}

export async function fetchDatasetVersions(datasetId: string) {
  return parseJson<{ items: DataPlaneVersion[] }>(
    await ceApi(`/api/data/datasets/${encodeURIComponent(datasetId)}/versions`),
    "Failed to load dataset versions",
  );
}

export async function queryDataDataset(datasetId: string, sql: string) {
  return parseJson<DataQueryResult>(
    await ceApi("/api/data/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset_id: datasetId, sql }),
    }),
    "Failed to run query",
  );
}

export async function exportDataDataset(datasetId: string, format = "csv") {
  return parseJson<{ dataset_id: string; path: string; format: string; bytes?: number }>(
    await ceApi(`/api/data/export${qs({ dataset_id: datasetId, format })}`, {
      method: "POST",
    }),
    "Failed to export dataset",
  );
}

export async function deleteDataDataset(datasetId: string) {
  return parseJson<{ deleted: boolean }>(
    await ceApi(`/api/data/datasets/${encodeURIComponent(datasetId)}`, {
      method: "DELETE",
    }),
    "Failed to delete dataset",
  );
}
