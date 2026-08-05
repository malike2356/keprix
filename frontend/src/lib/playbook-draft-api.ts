import { ceApi } from "@/lib/ce-api";

export type PlaybookDraftResponse = {
  yaml_text: string;
  playbook_id: string;
  warnings: string[];
  model_id: string;
  run_spec: {
    graph_id: string;
    steps: Array<Record<string, unknown>>;
    edges: Array<Record<string, unknown>>;
    entry?: string;
  };
};

export async function draftPlaybookFromPrompt(body: {
  prompt: string;
  template_hint?: string;
  workspace_id?: string;
}): Promise<PlaybookDraftResponse> {
  const response = await ceApi("/api/playbooks/draft-from-prompt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = (payload as { detail?: { message?: string } | string }).detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail && typeof detail === "object" && "message" in detail
          ? String(detail.message)
          : "Failed to generate playbook YAML";
    throw new Error(message);
  }
  return response.json() as Promise<PlaybookDraftResponse>;
}
