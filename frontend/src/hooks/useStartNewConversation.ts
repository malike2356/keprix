"use client";

import { useRouter } from "next/navigation";
import * as React from "react";
import { mutate } from "swr";
import { createConversation } from "@/lib/workspace-api";

export function useStartNewConversation() {
  const router = useRouter();
  const [starting, setStarting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const startNewConversation = React.useCallback(
    async (title = "New conversation") => {
      setStarting(true);
      setError(null);
      try {
        const session = await createConversation(title);
        await Promise.all([
          mutate((key) => typeof key === "string" && key.startsWith("chat-sessions")),
          mutate("workspace-sessions"),
        ]);
        router.push(`/chat/${session.id}`);
        return session;
      } catch {
        setError("Could not create a conversation. Check that the API is running.");
        return null;
      } finally {
        setStarting(false);
      }
    },
    [router],
  );

  return { startNewConversation, starting, error };
}
