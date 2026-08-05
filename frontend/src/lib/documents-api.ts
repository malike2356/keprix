import { ceApi } from "@/lib/ce-api";

export type DocumentIndex = {
  index_id: string;
  name: string;
  user_id: string;
  documents: Array<Record<string, unknown>>;
};

export type DocumentQueryResult = {
  question: string;
  answer: string;
  citations: Array<{ source: string; snippet: string; score: number }>;
  retrieval_path: string[];
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

export async function fetchDocumentIndexes(userId = "default") {
  return parseJson<{ indexes: DocumentIndex[] }>(
    await ceApi(`/api/documents/indexes?user_id=${encodeURIComponent(userId)}`),
    "document indexes",
  );
}

export async function createDocumentIndex(name: string, userId = "default") {
  return parseJson<DocumentIndex>(
    await ceApi("/api/documents/indexes", {
      method: "POST",
      body: JSON.stringify({ name, user_id: userId }),
    }),
    "create document index",
  );
}

export async function queryDocuments(question: string, indexId?: string) {
  return parseJson<DocumentQueryResult>(
    await ceApi("/api/documents/query", {
      method: "POST",
      body: JSON.stringify({ question, index_id: indexId, evidence_first: true }),
    }),
    "document query",
  );
}

export async function inspectDocumentIndex(indexId: string) {
  return parseJson<{ coverage: Record<string, unknown>; stale_documents: Array<Record<string, unknown>> }>(
    await ceApi(`/api/documents/indexes/${encodeURIComponent(indexId)}`),
    "inspect index",
  );
}

export async function refreshDocumentIndex(indexId: string) {
  return parseJson<{ index_id: string; refreshed_documents: number }>(
    await ceApi(`/api/documents/indexes/${encodeURIComponent(indexId)}/refresh`, { method: "POST" }),
    "refresh index",
  );
}

export async function deleteDocumentIndex(indexId: string) {
  return parseJson<{ deleted: boolean }>(
    await ceApi(`/api/documents/indexes/${encodeURIComponent(indexId)}`, { method: "DELETE" }),
    "delete index",
  );
}

export async function uploadToDocumentIndex(indexId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/documents/indexes/${encodeURIComponent(indexId)}/upload`, {
      method: "POST",
      body: form,
      headers: {},
    }),
    "upload to index",
  );
}

export async function fetchDocumentConnectors() {
  return parseJson<{ connectors: string[]; schemas: string[]; disk_roots?: string[] }>(
    await ceApi("/api/documents/connectors"),
    "document connectors",
  );
}

export async function extractDocumentStructure(text: string, schemaName = "generic") {
  return parseJson<Record<string, unknown>>(
    await ceApi("/api/documents/extract", {
      method: "POST",
      body: JSON.stringify({ text, schema_name: schemaName }),
    }),
    "extract failed",
  );
}

export type DiskFolderSource = {
  id: string;
  name: string;
  path: string;
  index_id: string;
  recursive: boolean;
  file_count: number;
  last_sync_at?: string | null;
  last_sync_error?: string | null;
  also_import_workspace?: boolean;
  initial_sync?: Record<string, unknown>;
};

export async function fetchDiskFolders(userId = "default") {
  return parseJson<{ folders: DiskFolderSource[]; disk_roots: string[] }>(
    await ceApi(`/api/documents/disk-folders?user_id=${encodeURIComponent(userId)}`),
    "disk folders",
  );
}

export async function addDiskFolder(body: {
  path: string;
  name?: string;
  index_id?: string;
  recursive?: boolean;
  also_import_workspace?: boolean;
  user_id?: string;
}) {
  return parseJson<DiskFolderSource>(
    await ceApi("/api/documents/disk-folders", {
      method: "POST",
      body: JSON.stringify({ user_id: "default", recursive: true, ...body }),
    }),
    "add disk folder",
  );
}

export async function syncDiskFolder(folderId: string, userId = "default") {
  return parseJson<Record<string, unknown>>(
    await ceApi(
      `/api/documents/disk-folders/${encodeURIComponent(folderId)}/sync?user_id=${encodeURIComponent(userId)}`,
      { method: "POST" },
    ),
    "sync disk folder",
  );
}

export async function deleteDiskFolder(folderId: string, userId = "default") {
  return parseJson<{ deleted: boolean }>(
    await ceApi(
      `/api/documents/disk-folders/${encodeURIComponent(folderId)}?user_id=${encodeURIComponent(userId)}`,
      { method: "DELETE" },
    ),
    "delete disk folder",
  );
}

export async function ingestDiskPath(indexId: string, path: string) {
  return parseJson<Record<string, unknown>>(
    await ceApi(`/api/documents/indexes/${encodeURIComponent(indexId)}/disk-path`, {
      method: "POST",
      body: JSON.stringify({ path }),
    }),
    "ingest disk path",
  );
}
