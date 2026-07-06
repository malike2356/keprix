"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { PLAYBOOK_PHASES } from "@/lib/opportunity-api";

type Props = {
  completedPhases?: string[];
  currentPhase?: string | null;
};

export default function OpportunityTimeline({ completedPhases = [], currentPhase }: Props) {
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
      {PLAYBOOK_PHASES.map((phase) => {
        const done = completedPhases.includes(phase);
        const active = currentPhase === phase;
        return (
          <Box
            key={phase}
            sx={{
              px: 1,
              py: 0.5,
              borderRadius: 1,
              border: 1,
              borderColor: active ? "primary.main" : "divider",
              bgcolor: done ? "action.selected" : "transparent",
              fontSize: 12,
            }}
          >
            <Typography variant="caption" component="span">
              {phase.replace(/_/g, " ")}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}
