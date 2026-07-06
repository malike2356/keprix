"use client";

import Box from "@mui/material/Box";
import * as React from "react";
import useSWR from "swr";
import CanvasPanel from "@/components/chat/CanvasPanel";
import ChatEmptyState from "@/components/chat/ChatEmptyState";
import ChatErrorBanner from "@/components/chat/ChatErrorBanner";
import ChatStatusBar from "@/components/chat/ChatStatusBar";
import ThinkingBlock from "@/components/chat/ThinkingBlock";
import ChatWorkspaceShell from "@/components/workspace/ChatWorkspaceShell";
import ChatInputBar from "@/components/workspace/ChatInputBar";
import MessageFeed from "@/components/workspace/MessageFeed";
import { useCESession } from "@/lib/ce-auth";
import { extractCanvasBlocks } from "@/lib/canvas-blocks";
import { useChat, useResolvedModel } from "@/hooks/useChat";
import {
  fetchAvailableModels,
  fetchConversation,
  fetchConversations,
} from "@/lib/workspace-api";

type ChatSessionPageProps = {
  params: Promise<{ sessionId: string }>;
};

export default function ChatSessionPage({ params }: ChatSessionPageProps) {
  const { sessionId } = React.use(params);
  const { user } = useCESession();
  const { messages, send, stop, isStreaming, updateMutationStatus } = useChat(sessionId);
  const [title, setTitle] = React.useState("Conversation");
  const [error, setError] = React.useState<string | null>(null);

  const { data: models = [] } = useSWR("workspace-models", fetchAvailableModels);
  const [activeModelId, selectModel] = useResolvedModel(models);
  const { data: sessions = [] } = useSWR("chat-sessions", () => fetchConversations(50));

  React.useEffect(() => {
    fetchConversation(sessionId)
      .then((data) => setTitle(data.title || "Conversation"))
      .catch(() => setTitle("Conversation"));
  }, [sessionId]);

  const initials = (user?.username || "U").slice(0, 2).toUpperCase();
  const isOwner = user?.role === "admin" || user?.role === "owner";
  const canvasBlocks = React.useMemo(() => extractCanvasBlocks(messages), [messages]);
  const [canvasOpen, setCanvasOpen] = React.useState(false);
  const [canvasWidth, setCanvasWidth] = React.useState(360);

  const activeModel = models.find((item) => item.id === activeModelId) || null;
  const lastAssistant = [...messages].reverse().find((message) => message.role === "assistant");
  const thinkingBlocks = lastAssistant?.content || [];

  React.useEffect(() => {
    if (canvasBlocks.length > 0) {
      setCanvasOpen(true);
    }
  }, [canvasBlocks.length]);

  const handleSend = async (text: string, fileIds: string[]) => {
    setError(null);
    try {
      await send(text, fileIds);
    } catch {
      setError("Message failed. Check the API connection and try again.");
    }
  };

  const handleStarter = (prompt: string) => {
    void handleSend(prompt, []);
  };

  return (
    <ChatWorkspaceShell sessionId={sessionId} sessionTitle={title}>
      <Box sx={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
        {error ? <ChatErrorBanner message={error} onDismiss={() => setError(null)} onRetry={() => setError(null)} /> : null}
        <Box sx={{ display: "flex", flex: 1, minHeight: 0 }}>
          <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", minHeight: 0 }}>
            <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", display: "flex", flexDirection: "column" }}>
              {messages.length === 0 && !isStreaming ? (
                <ChatEmptyState onPromptSelect={handleStarter} />
              ) : (
                <>
                  <ThinkingBlock blocks={thinkingBlocks} isStreaming={isStreaming} />
                  <MessageFeed
                    messages={messages}
                    sessionId={sessionId}
                    isStreaming={isStreaming}
                    userInitials={initials}
                    canApprove={isOwner}
                    canOpenFiles={isOwner}
                    onMutationStatusChange={(mutationId, status, retryMessage, persistedMessage) =>
                      updateMutationStatus(mutationId, status, retryMessage, persistedMessage)
                    }
                  />
                </>
              )}
            </Box>
            <Box sx={{ flexShrink: 0 }}>
              <ChatStatusBar
                model={activeModel}
                models={models}
                modelId={activeModelId}
                onModelChange={selectModel}
                isStreaming={isStreaming}
                onStop={stop}
                sessionCount={sessions.length}
                connected
              />
              <ChatInputBar onSend={handleSend} onStop={stop} isStreaming={isStreaming} />
            </Box>
          </Box>
          <CanvasPanel
            open={canvasOpen}
            blocks={canvasBlocks}
            onClose={() => setCanvasOpen(false)}
            width={canvasWidth}
            onWidthChange={setCanvasWidth}
          />
        </Box>
      </Box>
    </ChatWorkspaceShell>
  );
}
