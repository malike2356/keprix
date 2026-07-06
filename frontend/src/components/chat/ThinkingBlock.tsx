"use client";

import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { keyframes } from "@mui/material/styles";
import * as React from "react";
import type { MessageBlock } from "@/lib/workspace-api";

type ThinkingBlockProps = {
  blocks: MessageBlock[];
  isStreaming?: boolean;
};

const pulse = keyframes`
  0%, 100% { opacity: 0.55; }
  50% { opacity: 1; }
`;

function thinkingContent(blocks: MessageBlock[]) {
  return blocks
    .filter((block) => block.type === "thinking")
    .map((block) => block.content)
    .join("\n")
    .trim();
}

function toolSteps(blocks: MessageBlock[]) {
  return blocks.filter((block) => block.type === "tool_call");
}

export default function ThinkingBlock({ blocks, isStreaming = false }: ThinkingBlockProps) {
  const thinking = thinkingContent(blocks);
  const steps = toolSteps(blocks);
  const [open, setOpen] = React.useState(false);

  React.useEffect(() => {
    if (isStreaming && (thinking || steps.length > 0)) {
      setOpen(true);
      return;
    }
    if (!isStreaming && (thinking || steps.length > 0)) {
      setOpen(false);
    }
  }, [isStreaming, thinking, steps.length]);

  if (!thinking && steps.length === 0 && !isStreaming) {
    return null;
  }

  if (!thinking && steps.length === 0 && isStreaming) {
    return (
      <Box sx={{ mx: { xs: 1, md: 3 }, mb: 2 }}>
        <Typography
          variant="caption"
          sx={{
            display: "inline-flex",
            alignItems: "center",
            gap: 1,
            px: 1.5,
            py: 0.5,
            borderRadius: 999,
            bgcolor: "action.hover",
            color: "text.secondary",
            animation: `${pulse} 1.4s ease-in-out infinite`,
          }}
        >
          Thinking...
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        mx: { xs: 1, md: 3 },
        mb: 2,
        border: "1px dashed",
        borderColor: "divider",
        borderRadius: 2,
        bgcolor: "background.paper",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 2,
          py: 1,
          cursor: "pointer",
        }}
        onClick={() => setOpen((value) => !value)}
      >
        <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>
          {thinking ? "Thinking" : "Agent activity"}
          {steps.length > 0 ? ` (${steps.length} step${steps.length === 1 ? "" : "s"})` : ""}
          {isStreaming ? " ..." : ""}
        </Typography>
        <IconButton size="small" onClick={() => setOpen((value) => !value)} aria-label="Toggle thinking">
          {open ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </IconButton>
      </Box>
      <Collapse in={open}>
        <Box sx={{ px: 2, pb: 2, display: "grid", gap: 1.5 }}>
          {thinking ? (
            <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: "pre-wrap", fontSize: "0.85rem" }}>
              {thinking}
            </Typography>
          ) : null}
          {steps.map((step, index) => (
            <Box key={`${step.name}-${index}`}>
              <Typography variant="caption" color="text.secondary">
                {step.status === "running" ? "running" : step.status === "error" ? "failed" : "done"}
                {": "}
                {step.name}
              </Typography>
              {step.output ? (
                <Typography
                  variant="caption"
                  component="pre"
                  sx={{
                    mt: 0.5,
                    whiteSpace: "pre-wrap",
                    color: step.status === "error" ? "error.main" : "text.secondary",
                    fontFamily: "monospace",
                  }}
                >
                  {step.output.slice(0, 400)}
                  {step.output.length > 400 ? "..." : ""}
                </Typography>
              ) : null}
            </Box>
          ))}
        </Box>
      </Collapse>
    </Box>
  );
}
