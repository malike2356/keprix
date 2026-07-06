"use client";

import useSWR from "swr";
import { deleteConversation, fetchConversations, type WorkspaceSession } from "@/lib/workspace-api";

export function useSessionList(limit = 50) {
  const { data, mutate, isLoading } = useSWR(`chat-sessions-${limit}`, () => fetchConversations(limit), {
    refreshInterval: 30_000,
  });
  const sessions: WorkspaceSession[] = data || [];

  const remove = async (sessionId: string) => {
    await deleteConversation(sessionId);
    await mutate();
  };

  return { sessions, refresh: mutate, remove, isLoading };
}
