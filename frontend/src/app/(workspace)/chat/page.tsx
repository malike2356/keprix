"use client";

import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import * as React from "react";
import ChatEmptyState from "@/components/chat/ChatEmptyState";
import KeprixWordmark from "@/components/chat/KeprixWordmark";
import { useStartNewConversation } from "@/hooks/useStartNewConversation";

export default function NewChatPage() {
  const { startNewConversation, starting, error } = useStartNewConversation();

  if (starting) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", height: "100%", gap: 2 }}>
        <KeprixWordmark size="lg" />
        <CircularProgress size={28} />
        <Typography color="text.secondary">Starting new conversation...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: "100%", overflow: "auto", display: "flex", flexDirection: "column" }}>
      {error ? (
        <Typography color="error" sx={{ textAlign: "center", mt: 4 }}>
          {error}
        </Typography>
      ) : null}
      <ChatEmptyState
        onPromptSelect={(prompt) => {
          void startNewConversation(prompt.slice(0, 80));
        }}
        onStartBlank={() => {
          void startNewConversation();
        }}
      />
    </Box>
  );
}
