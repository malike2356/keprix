import { ceApi } from "@/lib/ce-api";

export type FsEntry = {
  name: string;
  path: string;
  isDirectory: boolean;
  size?: number;
  modified_at?: string;
};

export type FsListResult = {
  entries: FsEntry[];
  error?: string;
  message?: string;
  path?: string;
  count?: number;
};

export type FsReadTextResult = {
  binary: boolean;
  byteSize: number;
  language: string;
  mimeType: string;
  path: string;
  text: string;
  truncated: boolean;
};

export type FsDefaultCwd = {
  cwd: string;
  branch: string;
  shortcuts?: {
    data?: string;
    home?: string;
    docs?: string;
  };
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

function fileQuery(path: string): string {
  return `?path=${encodeURIComponent(path)}`;
}

export function humanizeFsError(code?: string, message?: string): string {
  if (message && message !== "Not Found") return message;
  switch (code) {
    case "ENOENT":
      return "Path not found";
    case "ENOTDIR":
      return "Not a directory";
    case "EACCES":
      return "Permission denied";
    default:
      return code || message || "Failed to read path";
  }
}

export async function listFilesystemEntries(path: string): Promise<FsListResult> {
  return parseJson<FsListResult>(
    await ceApi(`/api/fs/list${fileQuery(path)}`),
    "Failed to list filesystem entries",
  );
}

export async function readFilesystemText(path: string): Promise<FsReadTextResult> {
  return parseJson<FsReadTextResult>(
    await ceApi(`/api/fs/read-text${fileQuery(path)}`),
    "Failed to read file",
  );
}

export async function readFilesystemDataUrl(path: string): Promise<string> {
  const data = await parseJson<{ dataUrl: string }>(
    await ceApi(`/api/fs/read-data-url${fileQuery(path)}`),
    "Failed to load preview data",
  );
  return data.dataUrl;
}

export async function getFilesystemGitRoot(path: string): Promise<string | null> {
  const data = await parseJson<{ root: string | null }>(
    await ceApi(`/api/fs/git-root${fileQuery(path)}`),
    "Failed to resolve git root",
  );
  return data.root;
}

export async function getFilesystemDefaultCwd(): Promise<FsDefaultCwd | null> {
  const response = await ceApi("/api/fs/default-cwd");
  if (!response.ok) {
    return null;
  }
  return response.json();
}

export async function mkdirFilesystem(path: string): Promise<{ path: string }> {
  return parseJson(
    await ceApi("/api/fs/mkdir", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),
    "Failed to create folder",
  );
}

export async function uploadFilesystemFile(directory: string, file: File): Promise<{ path: string }> {
  const form = new FormData();
  form.append("path", directory);
  form.append("file", file);
  return parseJson(
    await ceApi("/api/fs/upload", {
      method: "POST",
      body: form,
    }),
    "Upload failed",
  );
}

export async function importFilesystemPathToDocuments(path: string): Promise<{ id: string; title: string }> {
  return parseJson(
    await ceApi("/api/fs/import-to-documents", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),
    "Import to Documents failed",
  );
}
