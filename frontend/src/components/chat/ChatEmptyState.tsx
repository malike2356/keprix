"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import KeprixWordmark from "@/components/chat/KeprixWordmark";
import KeprixWatermark from "@/components/shared/KeprixWatermark";

const STARTERS = [
  "Track my time on this project",
  "Summarise what Keprix can do in this workspace",
  "Help me configure an LLM provider",
  "Show me what tools are available",
];

type ChatEmptyStateProps = {
  onPromptSelect: (prompt: string) => void;
  onStartBlank?: () => void;
};

export default function ChatEmptyState({ onPromptSelect, onStartBlank }: ChatEmptyStateProps) {
  return (
    <Box
      sx={{
        position: "relative",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        flex: 1,
        minHeight: "100%",
        px: 2,
        py: 4,
        gap: 3,
        overflow: "hidden",
      }}
    >
      <KeprixWatermark opacity={0.07} size="min(68vmin, 480px)" />
      <Box
        sx={{
          position: "relative",
          zIndex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 3,
          width: "100%",
        }}
      >
        <KeprixWordmark size="hero" />
        <Typography variant="h6" color="text.secondary" sx={{ fontWeight: 500 }}>
          The Mutant AI OS
        </Typography>
        <Typography color="text.secondary" sx={{ maxWidth: 480, textAlign: "center" }}>
          Start a conversation with your agent. Pick a prompt below or type your own message.
        </Typography>
        <Stack spacing={1.5} sx={{ width: "100%", maxWidth: 520 }}>
          {onStartBlank ? (
            <Button variant="contained" onClick={onStartBlank} sx={{ py: 1.25 }}>
              Start blank conversation
            </Button>
          ) : null}
          {STARTERS.map((prompt) => (
            <Button
              key={prompt}
              variant="outlined"
              onClick={() => onPromptSelect(prompt)}
              sx={{
                justifyContent: "flex-start",
                textAlign: "left",
                py: 1.25,
                borderColor: "divider",
                color: "text.primary",
              }}
            >
              {prompt}
            </Button>
          ))}
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 480, textAlign: "center" }}>
          Or click the microphone to speak your message.
        </Typography>
      </Box>
    </Box>
  );
}
