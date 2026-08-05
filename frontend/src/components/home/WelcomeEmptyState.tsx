"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import { useRouter } from "next/navigation";
import { createConversation } from "@/lib/workspace-api";

const SUGGESTIONS = [
  "Help me debug this Python traceback",
  "Write a bash script to batch rename files",
  "Review this code for security issues",
  "Explain how this function works",
];

export default function WelcomeEmptyState() {
  const router = useRouter();

  async function handleSuggestion(text: string) {
    const conv = await createConversation(text.slice(0, 80));
    router.push(`/chat/${conv.id}?prefill=${encodeURIComponent(text)}`);
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        flex: 1,
        py: 10,
        px: 4,
        textAlign: "center",
      }}
    >
      <Typography variant="h5" fontWeight={600} gutterBottom>
        Your agent is ready.
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 380, mb: 4 }}>
        Start a session and it will remember what matters, build skills over time, and get better
        at working with you.
      </Typography>

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mb: 4 }}>
        <Button component={NextLink} href="/chat" variant="contained" size="large">
          Start a session
        </Button>
        <Button component={NextLink} href="/files" variant="outlined" size="large">
          Open files
        </Button>
      </Stack>

      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, justifyContent: "center", maxWidth: 480 }}>
        {SUGGESTIONS.map((s) => (
          <Chip
            key={s}
            label={s}
            variant="outlined"
            clickable
            onClick={() => handleSuggestion(s)}
            size="small"
          />
        ))}
      </Box>
    </Box>
  );
}
