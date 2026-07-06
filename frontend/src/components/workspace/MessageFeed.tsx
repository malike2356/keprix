"use client";

import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import Box from "@mui/material/Box";
import Fab from "@mui/material/Fab";
import * as React from "react";
import TypingIndicator from "@/components/chat/TypingIndicator";
import AgentMessage from "@/components/workspace/AgentMessage";
import SystemMessage from "@/components/workspace/SystemMessage";
import UserMessage from "@/components/workspace/UserMessage";
import type { WorkspaceMessage } from "@/lib/workspace-api";

type MessageFeedProps = {
  messages: WorkspaceMessage[];
  sessionId?: string;
  isStreaming?: boolean;
  userInitials: string;
  canApprove?: boolean;
  canOpenFiles?: boolean;
  onMutationStatusChange?: (
    mutationId: string,
    status: "approved" | "rejected",
    retryMessage?: string,
    message?: WorkspaceMessage,
  ) => void;
};

export default function MessageFeed({
  messages,
  sessionId,
  isStreaming = false,
  userInitials,
  canApprove = false,
  canOpenFiles = false,
  onMutationStatusChange,
}: MessageFeedProps) {
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const bottomRef = React.useRef<HTMLDivElement | null>(null);
  const [showJump, setShowJump] = React.useState(false);
  const pinnedToBottom = React.useRef(true);

  const scrollToBottom = React.useCallback((behavior: ScrollBehavior = "smooth") => {
    bottomRef.current?.scrollIntoView({ behavior, block: "end" });
  }, []);

  React.useEffect(() => {
    if (pinnedToBottom.current) {
      scrollToBottom(isStreaming ? "auto" : "smooth");
    }
  }, [messages, isStreaming, scrollToBottom]);

  const onScroll = (event: React.UIEvent<HTMLDivElement>) => {
    const node = event.currentTarget;
    const distance = node.scrollHeight - node.scrollTop - node.clientHeight;
    const nearBottom = distance < 80;
    pinnedToBottom.current = nearBottom;
    setShowJump(!nearBottom);
  };

  return (
    <Box sx={{ position: "relative", flex: 1, minHeight: 0 }}>
      <Box
        ref={containerRef}
        onScroll={onScroll}
        sx={{
          px: { xs: 1, md: 3 },
          py: 2,
          minHeight: "100%",
          height: "100%",
          overflow: "auto",
        }}
      >
          {messages.length === 0 ? (
            <Box sx={{ color: "text.secondary", textAlign: "center", mt: 8 }}>
              Send a message to start working with your agent.
            </Box>
          ) : null}
          {messages.map((message) => {
            if (message.role === "system") {
              return <SystemMessage key={message.id} message={message} />;
            }
            if (message.role === "user") {
              return <UserMessage key={message.id} message={message} initials={userInitials} />;
            }
            return (
              <AgentMessage
                key={message.id}
                message={message}
                sessionId={sessionId}
                canApprove={canApprove}
                canOpenFiles={canOpenFiles}
                onMutationStatusChange={onMutationStatusChange}
              />
            );
          })}
          {isStreaming ? <TypingIndicator /> : null}
          <Box ref={bottomRef} />
        </Box>
      {showJump ? (
        <Fab
          size="small"
          color="primary"
          onClick={() => {
            pinnedToBottom.current = true;
            scrollToBottom();
          }}
          sx={{ position: "absolute", right: 16, bottom: 16 }}
          aria-label="Scroll to bottom"
        >
          <KeyboardArrowDownIcon />
        </Fab>
      ) : null}
    </Box>
  );
}
