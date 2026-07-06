import { ceApi } from "@/lib/ce-api";

export type LocalizationCorrection = {
  id: string;
  audit_record_id: string;
  workspace_id: string;
  correction_type: string;
  original_value: string;
  corrected_value: string;
  source_language: string;
  target_language: string | null;
  domain: string;
  status: string;
  submitted_at: string | null;
  submitted_by_user_id: string | null;
  audit_record?: Record<string, unknown> | null;
};

export type LocalizationMetrics = {
  correction_rate: {
    correction_rate: number;
    corrections_approved: number;
    audit_records: number;
    by_type: Record<string, number>;
  };
  coverage: {
    interaction_count: number;
    correction_count: number;
    training_samples_staged: number;
    training_samples_exported: number;
    readiness_by_language: Record<
      string,
      { staged_samples: number; exported_samples: number; ready_for_export: boolean; threshold: number }
    >;
  };
  provider_accuracy: {
    providers: Array<{
      provider: string;
      language: string;
      month: string;
      correction_rate: number;
      needs_investigation: boolean;
      total_responses?: number;
      total_corrections?: number;
    }>;
  };
};

const WORKSPACE_ID = "default";

export async function fetchCorrections(status?: string): Promise<LocalizationCorrection[]> {
  const params = new URLSearchParams({ workspace_id: WORKSPACE_ID });
  if (status) params.set("status", status);
  const response = await ceApi(`/api/localization/corrections?${params.toString()}`);
  if (!response.ok) throw new Error("Failed to load corrections");
  const payload = await response.json();
  return payload.corrections ?? [];
}

export async function fetchCorrection(id: string): Promise<LocalizationCorrection> {
  const response = await ceApi(`/api/localization/corrections/${id}?workspace_id=${WORKSPACE_ID}`);
  if (!response.ok) throw new Error("Failed to load correction");
  const payload = await response.json();
  return { ...payload.correction, audit_record: payload.audit_record };
}

export async function approveCorrection(id: string, qualityScore: number, correctedValue?: string) {
  const response = await ceApi(`/api/localization/corrections/${id}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quality_score: qualityScore, corrected_value: correctedValue }),
  });
  if (!response.ok) throw new Error("Failed to approve correction");
  return response.json();
}

export async function rejectCorrection(id: string, reason: string) {
  const response = await ceApi(`/api/localization/corrections/${id}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) throw new Error("Failed to reject correction");
  return response.json();
}

export async function fetchLocalizationMetrics(): Promise<LocalizationMetrics> {
  const response = await ceApi(`/api/localization/metrics?workspace_id=${WORKSPACE_ID}`);
  if (!response.ok) throw new Error("Failed to load localization metrics");
  return response.json();
}

export async function fetchTopCorrectedTerms(domain: string, languageCode: string) {
  const params = new URLSearchParams({
    workspace_id: WORKSPACE_ID,
    domain,
    language_code: languageCode,
    limit: "20",
  });
  const response = await ceApi(`/api/localization/metrics/top-errors?${params.toString()}`);
  if (!response.ok) throw new Error("Failed to load top corrected terms");
  return response.json();
}

export async function batchApproveCorrections(correctionIds: string[], qualityScore: number) {
  const response = await ceApi("/api/localization/corrections/batch/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ correction_ids: correctionIds, quality_score: qualityScore }),
  });
  if (!response.ok) throw new Error("Failed to batch approve corrections");
  return response.json();
}

export type GlossaryRecord = {
  id: string;
  domain: string;
  entries: Array<{
    term: string;
    approved_equivalent: string;
    notes?: string;
    forbidden_translations?: string[];
  }>;
};

export async function fetchGlossaries(): Promise<GlossaryRecord[]> {
  const response = await ceApi("/api/localization/glossaries");
  if (!response.ok) throw new Error("Failed to load glossaries");
  const payload = await response.json();
  return payload.glossaries ?? [];
}

export async function saveGlossary(glossary: GlossaryRecord): Promise<GlossaryRecord> {
  const response = await ceApi("/api/localization/glossaries", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(glossary),
  });
  if (!response.ok) throw new Error("Failed to save glossary");
  const payload = await response.json();
  return payload.glossary;
}

export async function addGlossaryTerm(domain: string, sourceTerm: string, translatedTerm: string) {
  const glossaries = await fetchGlossaries();
  const glossary =
    glossaries.find((item) => item.domain === domain) ??
    ({
      id: `${domain}_v1`,
      domain,
      entries: [],
    } as GlossaryRecord);
  const entries = [...(glossary.entries ?? [])];
  const existing = entries.find((entry) => entry.term.toLowerCase() === sourceTerm.toLowerCase());
  const payload = {
    term: sourceTerm,
    approved_equivalent: translatedTerm,
    notes: "Added from localization metrics dashboard",
    forbidden_translations: existing?.forbidden_translations ?? [],
  };
  if (existing) {
    const index = entries.indexOf(existing);
    entries[index] = { ...existing, ...payload };
  } else {
    entries.push(payload);
  }
  return saveGlossary({ ...glossary, entries });
}

export async function exportFlywheel(outputPath: string) {
  const response = await ceApi("/api/localization/flywheel/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ output_path: outputPath, workspace_id: WORKSPACE_ID }),
  });
  if (!response.ok) throw new Error("Failed to export flywheel data");
  return response.json();
}
