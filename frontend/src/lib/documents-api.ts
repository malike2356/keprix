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
