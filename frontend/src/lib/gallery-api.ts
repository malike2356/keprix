import { buildApiHeaders, ceApi, getApiBaseUrl } from "@/lib/ce-api";

export type GalleryImage = {
  id: string;
  filename: string;
  url: string;
  width?: number;
  height?: number;
  created_at?: string;
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

export async function fetchGalleryImages(): Promise<GalleryImage[]> {
  const data = await parseJson<{ items: GalleryImage[] }>(
    await ceApi("/api/workspace/gallery"),
    "Failed to load gallery",
  );
  return data.items;
}

export async function uploadGalleryImage(file: File): Promise<GalleryImage> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${getApiBaseUrl()}/api/workspace/gallery/upload`, {
    method: "POST",
    headers: buildApiHeaders(),
    body: form,
    credentials: "include",
  });
  const data = await parseJson<{ item: GalleryImage }>(response, "Upload failed");
  return data.item;
}

export async function deleteGalleryImage(imageId: string): Promise<void> {
  await parseJson(
    await ceApi(`/api/workspace/gallery/${imageId}`, { method: "DELETE" }),
    "Delete failed",
  );
}

export function galleryImageUrl(image: GalleryImage): string {
  if (image.url.startsWith("http")) {
    return image.url;
  }
  return `${getApiBaseUrl()}${image.url}`;
}
