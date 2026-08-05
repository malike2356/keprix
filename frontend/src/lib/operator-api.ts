import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type OperatorContextBundle = {
  staged_mutations: number;
  interrupted_playbooks: number;
  channel_issues: Array<{ id?: string; name?: string; status?: string; detail?: string }>;
  recent_failed_runs: Array<{
    run_id?: string;
    graph_id?: string;
    status?: string;
    error?: string;
  }>;
  summary_markdown: string;
};

export type OperatorCopilotEvent = {
  event: string;
  content?: string;
  action?: string;
  action_id?: string;
  record_id?: string;
  run_id?: string;
  summary?: string;
  name?: string;
  message?: unknown;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return payload as T;
}

export async function fetchOperatorContext(
  workspaceId = "default",
  detail: "nav" | "full" = "nav",
): Promise<OperatorContextBundle> {
  const params = new URLSearchParams({
    workspace_id: workspaceId,
    detail,
  });
  const response = await ceApi(`/api/operator/context?${params.toString()}`);
  return parseJson(response, "Failed to load operator context");
}

export async function streamOperatorCopilotMessage(
  message: string,
  options?: {
    workspaceId?: string;
    confirmAction?: Record<string, unknown> | null;
    pagePath?: string | null;
    pageLabel?: string | null;
    signal?: AbortSignal;
    onEvent?: (event: OperatorCopilotEvent) => void;
  },
): Promise<string> {
  const response = await ceApi("/api/operator/copilot/message", {
    method: "POST",
    body: JSON.stringify({
      message,
      workspace_id: options?.workspaceId ?? "default",
      confirm_action: options?.confirmAction ?? null,
      page_path: options?.pagePath ?? null,
      page_label: options?.pageLabel ?? null,
    }),
    signal: options?.signal,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Operator copilot request failed"));
  }
  if (!response.body) {
    throw new Error("Operator copilot returned an empty body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let assembled = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      let event: OperatorCopilotEvent;
      try {
        event = JSON.parse(trimmed) as OperatorCopilotEvent;
      } catch {
        continue;
      }
      options?.onEvent?.(event);
      if (event.event === "text_delta" && typeof event.content === "string") {
        assembled += event.content;
      }
    }
  }

  if (buffer.trim()) {
    try {
      const event = JSON.parse(buffer.trim()) as OperatorCopilotEvent;
      options?.onEvent?.(event);
      if (event.event === "text_delta" && typeof event.content === "string") {
        assembled += event.content;
      }
    } catch {
      /* ignore trailing partial */
    }
  }

  return assembled;
}
