import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type DocumentExportRequest = {
  title: string;
  markdown?: string;
  content?: string;
  input_type?: string;
  document_type?: string;
  version?: string;
  prepared_by?: string;
  classification?: string;
  format?: "html" | "pdf";
  include_cover?: boolean;
  include_signatory?: boolean;
  signatory_data?: {
    name?: string;
    title?: string;
    date?: string;
  };
};

export type DocumentExportResult = {
  file_id: string;
  file_url: string;
  format_returned: string;
  filename: string;
  size_bytes?: number;
};

const RESTRICTED = new Set(["confidential", "secret", "restricted", "top secret"]);

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return response.json();
}

export function isRestrictedClassification(value: string | undefined): boolean {
  return RESTRICTED.has((value || "").trim().toLowerCase());
}

export async function createDocumentExport(body: DocumentExportRequest) {
  return parseJson<DocumentExportResult>(
    await ceApi("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to create export",
  );
}

export function exportDownloadHref(fileUrl: string): string {
  return fileUrl.startsWith("/") ? fileUrl : `/${fileUrl}`;
}
