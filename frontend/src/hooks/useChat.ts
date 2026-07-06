"use client";

import * as React from "react";
import { ceApi } from "@/lib/ce-api";
import {
  fetchConversation,
  normalizeMessages,
  type MessageBlock,
  type WorkspaceMessage,
} from "@/lib/workspace-api";

const MODEL_KEY = "keprix_selected_model";

export function getStoredModel(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(MODEL_KEY);
}

export function setStoredModel(modelId: string): void {
  localStorage.setItem(MODEL_KEY, modelId);
}

export function useResolvedModel(models: Array<{ id: string }>): [string, (modelId: string) => void] {
  const [modelId, setModelId] = React.useState("");

  React.useEffect(() => {
    if (models.length === 0) {
      setModelId("");
      return;
    }
    const stored = getStoredModel();
    const match = models.find((item) => item.id === stored);
    const next = match?.id ?? models[0].id;
    setModelId(next);
    if (!match) {
      setStoredModel(next);
    }
  }, [models]);

  const selectModel = React.useCallback((next: string) => {
    setModelId(next);
    setStoredModel(next);
  }, []);

  return [modelId, selectModel];
}

function emptyAssistant(): WorkspaceMessage {
  return {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    content: [],
    createdAt: new Date().toISOString(),
  };
}

function upsertStreamingText(blocks: MessageBlock[], delta: string): MessageBlock[] {
  const next = [...blocks];
  const last = next[next.length - 1];
  if (last?.type === "text") {
    next[next.length - 1] = { ...last, content: `${last.content}${delta}` };
    return next;
  }
  next.push({ type: "text", content: delta });
  return next;
}

function applyStreamEvent(blocks: MessageBlock[], event: Record<string, unknown>): MessageBlock[] {
  const kind = String(event.event || "");
  if (kind === "text_delta") {
    return upsertStreamingText(blocks, String(event.content || ""));
  }
  if (kind === "thinking" || kind === "thinking_delta") {
    const delta = String(event.content || "");
    const next = [...blocks];
    const last = next[next.length - 1];
    if (last?.type === "thinking") {
      next[next.length - 1] = { ...last, content: `${last.content}${delta}` };
      return next;
    }
    next.push({ type: "thinking", content: delta });
    return next;
  }
  if (kind === "tool_call") {
    const mode = event.mode === "dry_run" || event.mode === "live" ? event.mode : undefined;
    return [
      ...blocks,
      {
        type: "tool_call",
        name: String(event.name || "tool"),
        input: (event.input as Record<string, unknown>) || {},
        status: (event.status as "running") || "running",
        ...(mode ? { mode } : {}),
      },
    ];
  }
  if (kind === "tool_call_update") {
    return blocks.map((block) =>
      block.type === "tool_call" && block.name === event.name
        ? {
            ...block,
            output: String(event.output || ""),
            status: (event.status as "done" | "error") || "done",
          }
        : block,
    );
  }
  if (kind === "code") {
    return [
      ...blocks,
      {
        type: "code",
        language: String(event.language || "text"),
        content: String(event.content || ""),
      },
    ];
  }
  if (kind === "file") {
    return [
      ...blocks,
      {
        type: "file",
        path: String(event.path || ""),
        action: (event.action as "created") || "created",
      },
    ];
  }
  if (kind === "mutation") {
    return [
      ...blocks,
      {
        type: "mutation",
        id: event.id ? String(event.id) : undefined,
        toolName: String(event.toolName || "generated_tool"),
        approach: event.approach ? String(event.approach) : undefined,
        code: String(event.code || ""),
        skillYaml: String(event.skillYaml || ""),
        sandboxResult: String(event.sandboxResult || ""),
        sandboxExitCode: Number(event.sandboxExitCode || 0),
        sandboxStderr: String(event.sandboxStderr || ""),
        status: (event.status as "pending") || "pending",
      },
    ];
  }
  return blocks;
}

export function useChat(sessionId: string) {
  const [messages, setMessages] = React.useState<WorkspaceMessage[]>([]);
  const [isStreaming, setIsStreaming] = React.useState(false);
  const abortRef = React.useRef<AbortController | null>(null);

  React.useEffect(() => {
    let active = true;
    fetchConversation(sessionId)
      .then((data) => {
        if (active) {
          setMessages(normalizeMessages(data.messages || []));
        }
      })
      .catch(() => {
        if (active) setMessages([]);
      });
    return () => {
      active = false;
    };
  }, [sessionId]);

  const stop = React.useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  const send = React.useCallback(
    async (text: string, fileIds: string[] = []) => {
      const trimmed = text.trim();
      if (!trimmed || isStreaming) return;

      const userMessage: WorkspaceMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: [{ type: "text", content: trimmed }],
        createdAt: new Date().toISOString(),
      };
      const assistantDraft = emptyAssistant();
      setMessages((prev) => [...prev, userMessage, assistantDraft]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await ceApi(`/api/conversations/${sessionId}/messages`, {
          method: "POST",
          body: JSON.stringify({
            content: trimmed,
            file_ids: fileIds,
            model: getStoredModel(),
          }),
          signal: controller.signal,
        });
        if (!response.ok || !response.body) {
          throw new Error("stream failed");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.trim()) continue;
            const event = JSON.parse(line) as Record<string, unknown>;
            if (event.event === "message_done" && event.message) {
              const finalMessage = normalizeMessages([event.message as WorkspaceMessage])[0];
              setMessages((prev) => {
                const withoutDraft = prev.slice(0, -1);
                return [...withoutDraft, finalMessage];
              });
              continue;
            }
            setMessages((prev) => {
              const draft = prev[prev.length - 1];
              if (!draft || draft.role !== "assistant") return prev;
              const updated = {
                ...draft,
                content: applyStreamEvent(draft.content, event),
              };
              return [...prev.slice(0, -1), updated];
            });
          }
        }
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          setMessages((prev) => {
            const draft = prev[prev.length - 1];
            if (!draft || draft.role !== "assistant") return prev;
            const updated = {
              ...draft,
              content: [
                ...draft.content,
                { type: "text" as const, content: "Sorry, the agent stream failed." },
              ],
            };
            return [...prev.slice(0, -1), updated];
          });
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [isStreaming, sessionId],
  );

  const updateMutationStatus = React.useCallback(
    (
      mutationId: string,
      status: "approved" | "rejected",
      retryMessage?: string,
      persistedMessage?: WorkspaceMessage,
    ) => {
      setMessages((prev) => {
        const next = prev.map((message) => ({
          ...message,
          content: message.content.map((block) =>
            block.type === "mutation" && block.id === mutationId ? { ...block, status } : block,
          ),
        }));

        if (persistedMessage && !next.some((message) => message.id === persistedMessage.id)) {
          return [...next, normalizeMessages([persistedMessage])[0]];
        }

        if (status === "approved" && retryMessage && !persistedMessage) {
          const hasRetry = next.some((message) =>
            message.content.some(
              (block) => block.type === "text" && block.content.trim() === retryMessage.trim(),
            ),
          );
          if (!hasRetry) {
            next.push({
              id: `assistant-retry-${mutationId}`,
              role: "assistant",
              content: [{ type: "text", content: retryMessage }],
              createdAt: new Date().toISOString(),
            });
          }
        }

        return next;
      });
    },
    [],
  );

  return { messages, send, stop, isStreaming, updateMutationStatus };
}
