import { buildApiHeaders, ceApi, getApiBaseUrl } from "@/lib/ce-api";

export type GalleryGeneration = {
  prompt?: string;
  model?: string;
  source?: string;
  [key: string]: unknown;
};

export type GalleryImage = {
  id: string;
  filename: string;
  original_name?: string;
  title?: string;
  url: string;
  size_bytes?: number;
  width?: number;
  height?: number;
  created_at?: string;
  updated_at?: string;
  tags?: string[];
  folder?: string;
  favorite?: boolean;
  ocr_text?: string;
  ocr_at?: string | null;
  ocr_engine?: string | null;
  generation?: GalleryGeneration | null;
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

export async function fetchGalleryImages(params?: {
  q?: string;
  folder?: string;
  favorites?: boolean;
}): Promise<{ items: GalleryImage[]; folders: string[]; count: number }> {
  const query = new URLSearchParams();
  if (params?.q) query.set("q", params.q);
  if (params?.folder) query.set("folder", params.folder);
  if (params?.favorites) query.set("favorites", "true");
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return parseJson(
    await ceApi(`/api/workspace/gallery${suffix}`),
    "Failed to load gallery",
  );
}

export async function uploadGalleryImage(
  file: File,
  options?: { folder?: string; tags?: string; generation?: GalleryGeneration },
): Promise<GalleryImage> {
  const form = new FormData();
  form.append("file", file);
  if (options?.folder) form.append("folder", options.folder);
  if (options?.tags) form.append("tags", options.tags);
  if (options?.generation) form.append("generation_json", JSON.stringify(options.generation));
  const response = await fetch(`${getApiBaseUrl()}/api/workspace/gallery/upload`, {
    method: "POST",
    headers: buildApiHeaders(),
    body: form,
    credentials: "include",
  });
  const data = await parseJson<{ item: GalleryImage }>(response, "Upload failed");
  return data.item;
}

export async function patchGalleryImage(
  imageId: string,
  patch: Partial<Pick<GalleryImage, "title" | "folder" | "favorite" | "tags">>,
): Promise<GalleryImage> {
  const data = await parseJson<{ item: GalleryImage }>(
    await ceApi(`/api/workspace/gallery/${imageId}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
    "Update failed",
  );
  return data.item;
}

export async function ocrGalleryImage(imageId: string): Promise<{ item: GalleryImage; text: string; engine: string }> {
  return parseJson(
    await ceApi(`/api/workspace/gallery/${imageId}/ocr`, { method: "POST" }),
    "OCR failed",
  );
}

export async function importGalleryImageToDocuments(imageId: string): Promise<{ document: { id: string; title: string }; item: GalleryImage }> {
  return parseJson(
    await ceApi(`/api/workspace/gallery/${imageId}/import-to-documents`, { method: "POST" }),
    "Import to Documents failed",
  );
}

export async function deleteGalleryImage(imageId: string): Promise<void> {
  await parseJson(
    await ceApi(`/api/workspace/gallery/${imageId}`, { method: "DELETE" }),
    "Delete failed",
  );
}

export async function bulkDeleteGalleryImages(ids: string[]): Promise<number> {
  const data = await parseJson<{ removed: number }>(
    await ceApi("/api/workspace/gallery/bulk-delete", {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),
    "Bulk delete failed",
  );
  return data.removed;
}

export function galleryImageUrl(image: GalleryImage): string {
  if (image.url.startsWith("http")) {
    return image.url;
  }
  return `${getApiBaseUrl()}${image.url}`;
}

/** Fetch a gallery file with auth headers and return an object URL (caller must revoke). */
export async function fetchGalleryImageObjectUrl(image: GalleryImage): Promise<string> {
  const path = image.url.startsWith("http")
    ? image.url
    : image.url.startsWith("/")
      ? image.url
      : `/api/workspace/gallery/${image.id}/file`;
  const response = await ceApi(path);
  if (!response.ok) {
    throw new Error("Failed to load image");
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

export function humanSize(bytes?: number): string {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(idx === 0 ? 0 : 1)} ${units[idx]}`;
}
