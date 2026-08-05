"use client";

import { alpha, type Theme } from "@mui/material/styles";
import type { SxProps } from "@mui/material/styles";

/** Shared NotebookLM-style calm glass surface for Brain chrome. */
export const brainGlassSx: SxProps<Theme> = {
  bgcolor: (theme) => alpha(theme.palette.background.paper, theme.palette.mode === "dark" ? 0.82 : 0.92),
  backdropFilter: "blur(12px)",
  WebkitBackdropFilter: "blur(12px)",
  border: 1,
  borderColor: "divider",
  borderRadius: 1.5,
  boxShadow: "none",
};

export const KIND_LABELS: Record<string, string> = {
  memory: "Memory",
  skill: "Skill",
  task: "Task",
  tool: "Tool",
  session: "Session",
  document: "Document",
  source: "Source",
  entity: "Entity",
};

export function kindTitle(kind: string): string {
  return KIND_LABELS[kind] || kind.charAt(0).toUpperCase() + kind.slice(1);
}
