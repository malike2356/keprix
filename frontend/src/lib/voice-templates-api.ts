import { buildApiHeaders, ceApi, getApiBaseUrl } from "@/lib/ce-api";

export type VoiceTemplateCategory = {
  id: string;
  label: string;
  description: string | null;
  domain: string;
  is_dynamic: boolean;
  dynamic_placeholder: string | null;
  sort_order: number;
};

export type VoiceTemplate = {
  id: string;
  category_id: string;
  language_code: string;
  dialect_note: string | null;
  audio_file_id: string;
  transcript: string;
  transcript_english: string;
  duration_seconds: number;
  recorded_by: string | null;
  recorded_at: string | null;
  quality_rating: number | null;
  status: "pending" | "approved" | "rejected" | "archived";
  approved_by_user_id: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  play_count: number;
  workspace_id: string | null;
  created_at: string;
  audio_url: string | null;
};

export type CoverageLanguage = {
  total_categories: number;
  covered_categories: number;
  coverage_pct: number;
};

export const VOICE_LANGUAGE_OPTIONS = [
  { code: "ak-GH", label: "Twi (Akan)" },
  { code: "fan-GH", label: "Fante" },
  { code: "ee-GH", label: "Ewe" },
  { code: "gaa-GH", label: "Ga" },
  { code: "dag-GH", label: "Dagbani" },
  { code: "en-GB", label: "English (UK)" },
];

async function parseJson<T>(response: Response, label: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error((payload as { detail?: string }).detail || `Failed to load ${label}`);
  }
  return response.json() as Promise<T>;
}

export function voiceTemplateAudioUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  return `${getApiBaseUrl()}${path}`;
}

export async function fetchVoiceTemplateCategories(domain?: string): Promise<VoiceTemplateCategory[]> {
  const suffix = domain ? `?domain=${encodeURIComponent(domain)}` : "";
  return parseJson(await ceApi(`/api/voice-templates/categories${suffix}`), "voice categories");
}

export async function fetchVoiceTemplateCoverage(): Promise<Record<string, CoverageLanguage>> {
  const payload = await parseJson<{ languages: Record<string, CoverageLanguage> }>(
    await ceApi("/api/voice-templates/coverage"),
    "voice coverage",
  );
  return payload.languages;
}

export async function fetchVoiceTemplates(params?: {
  language_code?: string;
  category_id?: string;
  status?: string;
  workspace_id?: string;
}): Promise<VoiceTemplate[]> {
  const query = new URLSearchParams();
  if (params?.language_code) query.set("language_code", params.language_code);
  if (params?.category_id) query.set("category_id", params.category_id);
  if (params?.status) query.set("status", params.status);
  if (params?.workspace_id) query.set("workspace_id", params.workspace_id);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return parseJson(await ceApi(`/api/voice-templates${suffix}`), "voice templates");
}

export async function fetchVoiceTemplate(templateId: string): Promise<VoiceTemplate> {
  return parseJson(await ceApi(`/api/voice-templates/${encodeURIComponent(templateId)}`), "voice template");
}

export async function fetchVoiceTemplateFallbacks(): Promise<Record<string, string>> {
  return parseJson(await ceApi("/api/voice-templates/fallbacks"), "language fallbacks");
}

export async function saveVoiceTemplateFallback(languageCode: string, fallbackLanguageCode: string): Promise<Record<string, string>> {
  return parseJson(
    await ceApi("/api/voice-templates/fallbacks", {
      method: "PUT",
      body: JSON.stringify({
        language_code: languageCode,
        fallback_language_code: fallbackLanguageCode,
      }),
    }),
    "language fallback",
  );
}

export async function uploadVoiceTemplate(input: {
  file: File;
  category_id: string;
  language_code: string;
  transcript: string;
  transcript_english: string;
  recorded_by: string;
  recorded_at: string;
  dialect_note?: string;
  workspace_id?: string;
}): Promise<{ template_id: string; status: string }> {
  const form = new FormData();
  form.append("audio_file", input.file);
  form.append("category_id", input.category_id);
  form.append("language_code", input.language_code);
  form.append("transcript", input.transcript);
  form.append("transcript_english", input.transcript_english);
  form.append("recorded_by", input.recorded_by);
  form.append("recorded_at", input.recorded_at);
  if (input.dialect_note) form.append("dialect_note", input.dialect_note);
  if (input.workspace_id) form.append("workspace_id", input.workspace_id);
  const response = await fetch(`${getApiBaseUrl()}/api/voice-templates`, {
    method: "POST",
    headers: buildApiHeaders(),
    body: form,
    credentials: "include",
  });
  return parseJson(response, "voice template upload");
}

export async function approveVoiceTemplate(templateId: string, qualityRating: number): Promise<VoiceTemplate> {
  return parseJson(
    await ceApi(`/api/voice-templates/${encodeURIComponent(templateId)}/approve`, {
      method: "POST",
      body: JSON.stringify({ quality_rating: qualityRating }),
    }),
    "approve voice template",
  );
}

export async function rejectVoiceTemplate(templateId: string, reason: string): Promise<VoiceTemplate> {
  return parseJson(
    await ceApi(`/api/voice-templates/${encodeURIComponent(templateId)}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
    "reject voice template",
  );
}

export async function archiveVoiceTemplate(templateId: string): Promise<void> {
  await parseJson(
    await ceApi(`/api/voice-templates/${encodeURIComponent(templateId)}`, { method: "DELETE" }),
    "archive voice template",
  );
}
