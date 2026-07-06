"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import type { WorkspaceMessage } from "@/lib/workspace-api";

type SystemMessageProps = {
  message: WorkspaceMessage;
};

export default function SystemMessage({ message }: SystemMessageProps) {
  const text = message.content
    .filter((block) => block.type === "text")
    .map((block) => block.content)
    .join("\n");

  if (!text.trim()) return null;

  return (
    <Box sx={{ display: "flex", justifyContent: "center", mb: 2 }}>
      <Typography
        variant="caption"
        sx={{
          px: 2,
          py: 0.5,
          bgcolor: (theme) => alpha(theme.palette.divider, 0.5),
          borderRadius: 999,
          color: "text.secondary",
        }}
      >
        {text}
      </Typography>
    </Box>
  );
}
