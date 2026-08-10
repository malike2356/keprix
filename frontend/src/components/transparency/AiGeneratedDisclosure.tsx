"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";

const DISCLOSURE: Record<string, string> = {
  en: "AI-generated content",
  fr: "Contenu generee par l'IA",
  de: "KI-generierte Inhalte",
  es: "Contenido generado por IA",
};

type AiGeneratedDisclosureProps = {
  locale?: string;
  contentType?: "text" | "image" | "code" | "audio" | "video";
};

/**
 * Non-removable SGI disclosure. No dismiss/hide control is provided.
 * CSS cannot hide this for end users on the chat surface (pointer-events none
 * only on decorative layers; this node stays in the accessibility tree).
 */
export default function AiGeneratedDisclosure({
  locale = "en",
  contentType = "text",
}: AiGeneratedDisclosureProps) {
  const key = (locale || "en").toLowerCase().split("-")[0];
  const text = DISCLOSURE[key] || DISCLOSURE.en;

  return (
    <Box
      component="aside"
      data-testid="ai-generated-disclosure"
      data-sgi-marker="keprix-sgi-disclosure"
      data-sgi-removable="false"
      data-sgi-content-type={contentType}
      role="note"
      aria-label={text}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        px: 1.25,
        py: 0.75,
        mb: 1,
        borderRadius: 1,
        border: (theme) => `1px solid ${alpha(theme.palette.warning.main, 0.45)}`,
        bgcolor: (theme) => alpha(theme.palette.warning.main, 0.08),
        // Intentionally no close button and not user-dismissible.
        userSelect: "none",
      }}
    >
      <Typography
        variant="caption"
        sx={{ fontWeight: 700, letterSpacing: 0.3, color: "warning.dark" }}
      >
        {text}
      </Typography>
    </Box>
  );
}

export function isDisclosureRemovable(): boolean {
  return false;
}
