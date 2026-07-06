"use client";

import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { WorkspaceMessage } from "@/lib/workspace-api";

type UserMessageProps = {
  message: WorkspaceMessage;
  initials: string;
};

export default function UserMessage({ message, initials }: UserMessageProps) {
  const text = message.content
    .filter((block) => block.type === "text")
    .map((block) => block.content)
    .join("\n");

  return (
    <Box sx={{ display: "flex", justifyContent: "flex-end", flexDirection: "row-reverse", gap: 1.5, mb: 2, alignItems: "flex-start" }}>
      <Box
        sx={{
          maxWidth: { xs: "88%", md: "75%" },
          px: 2,
          py: 1.5,
          borderRadius: "18px 18px 4px 18px",
          bgcolor: (theme) => theme.palette.primary.main,
          color: (theme) => theme.palette.primary.contrastText,
          boxShadow: 1,
        }}
      >
        <Typography variant="body1" sx={{ whiteSpace: "pre-wrap" }}>
          {text}
        </Typography>
      </Box>
      <Avatar sx={{ width: 32, height: 32, fontSize: "0.75rem", fontWeight: 700, flexShrink: 0 }}>
        {initials}
      </Avatar>
    </Box>
  );
}
