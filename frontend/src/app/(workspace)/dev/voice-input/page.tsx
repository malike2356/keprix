"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { AIVoiceInputDemo } from "@/components/ui/ai-voice-input-demo";
import PageHeader from "@/components/ui/PageHeader";

export default function VoiceInputDevPage() {
  if (process.env.NODE_ENV !== "development") {
    return (
      <Box sx={{ p: 4 }}>
        <Typography variant="body1" color="text.secondary">
          Voice input dev tools are only available in development builds.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3, p: { xs: 2, md: 3 } }}>
      <PageHeader
        title="Voice input (dev)"
        description="Visual QA for the scoped Tailwind voice island and AIVoiceInput component."
      />
      <AIVoiceInputDemo />
    </Box>
  );
}
