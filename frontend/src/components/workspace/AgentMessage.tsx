"use client";

import FileOutputBlock from "@/components/workspace/blocks/FileOutputBlock";
import MutationCard from "@/components/workspace/blocks/MutationCard";
import TextBlock from "@/components/workspace/blocks/TextBlock";
import ToolCallBlock from "@/components/workspace/blocks/ToolCallBlock";
import CodeBlock from "@/components/workspace/blocks/CodeBlock";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import type { WorkspaceMessage } from "@/lib/workspace-api";

type AgentMessageProps = {
  message: WorkspaceMessage;
  sessionId?: string;
  canApprove?: boolean;
  canOpenFiles?: boolean;
  onMutationStatusChange?: (
    mutationId: string,
    status: "approved" | "rejected",
    retryMessage?: string,
    message?: WorkspaceMessage,
  ) => void;
};

export default function AgentMessage({
  message,
  sessionId,
  canApprove = false,
  canOpenFiles = false,
  onMutationStatusChange,
}: AgentMessageProps) {
  return (
    <Box sx={{ display: "flex", gap: 1.5, mb: 3, alignItems: "flex-start" }}>
      <Box
        sx={{
          width: 32,
          height: 32,
          borderRadius: "50%",
          bgcolor: (theme) => alpha(theme.palette.primary.main, 0.15),
          border: (theme) => `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          mt: 0.5,
        }}
      >
        <Typography sx={{ fontSize: "0.65rem", fontWeight: 700, color: "primary.main" }}>
          KP
        </Typography>
      </Box>
      <Box
        sx={{
          flex: 1,
          display: "grid",
          gap: 1.5,
          minWidth: 0,
          maxWidth: { xs: "88%", md: "75%" },
          px: 2,
          py: 1.5,
          borderRadius: "4px 18px 18px 18px",
          border: (theme) => `1px solid ${alpha(theme.palette.divider, 0.6)}`,
          bgcolor: "background.paper",
          boxShadow: 1,
        }}
      >
        {message.content.map((block, index) => {
          if (block.type === "thinking") {
            return (
              <Box
                key={`${message.id}-thinking-${index}`}
                sx={{
                  px: 1.5,
                  py: 1,
                  borderRadius: 1,
                  bgcolor: "action.hover",
                  border: 1,
                  borderColor: "divider",
                }}
              >
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: "block", mb: 0.5 }}>
                  Thinking
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: "pre-wrap", fontSize: "0.85rem" }}>
                  {block.content}
                </Typography>
              </Box>
            );
          }
          if (block.type === "text") {
            return <TextBlock key={`${message.id}-text-${index}`} content={block.content} />;
          }
          if (block.type === "tool_call") {
            return <ToolCallBlock key={`${message.id}-tool-${index}`} block={block} />;
          }
          if (block.type === "code") {
            return <CodeBlock key={`${message.id}-code-${index}`} language={block.language} content={block.content} />;
          }
          if (block.type === "file") {
            return (
              <FileOutputBlock
                key={`${message.id}-file-${index}`}
                block={block}
                canOpen={canOpenFiles}
              />
            );
          }
          if (block.type === "mutation") {
            return (
              <MutationCard
                key={`${message.id}-mutation-${index}`}
                block={block}
                sessionId={sessionId}
                canApprove={canApprove}
                onStatusChange={(status, retryMessage, persistedMessage) => {
                  if (block.id) {
                    onMutationStatusChange?.(block.id, status, retryMessage, persistedMessage);
                  }
                }}
              />
            );
          }
          return null;
        })}
      </Box>
    </Box>
  );
}
