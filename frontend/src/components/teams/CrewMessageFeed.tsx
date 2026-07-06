"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import MarkdownRenderer from "@/components/workspace/MarkdownRenderer";
import type { TeamRunEvent } from "@/lib/teams-api";

type CrewMessageFeedProps = {
  events: TeamRunEvent[];
  emptyLabel?: string;
};

function roleColor(role: string | null | undefined): "default" | "primary" | "secondary" | "info" {
  if (!role) return "default";
  if (role.includes("review") || role.includes("qa")) return "secondary";
  if (role.includes("coord") || role.includes("lead")) return "primary";
  return "info";
}

export default function CrewMessageFeed({ events, emptyLabel }: CrewMessageFeedProps) {
  if (!events.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        {emptyLabel || "No crew activity yet."}
      </Typography>
    );
  }

  return (
    <Stack spacing={1.5}>
      {events.map((event, index) => (
        <Paper key={`${event.timestamp}-${index}`} variant="outlined" sx={{ p: 1.5 }}>
          <Box sx={{ display: "flex", gap: 1, alignItems: "center", mb: 0.5, flexWrap: "wrap" }}>
            {event.role ? <Chip size="small" color={roleColor(event.role)} label={event.role} /> : null}
            {event.task_id ? <Chip size="small" variant="outlined" label={event.task_id} /> : null}
            <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
              {new Date(event.timestamp).toLocaleTimeString()}
            </Typography>
          </Box>
          <MarkdownRenderer content={event.content} />
        </Paper>
      ))}
    </Stack>
  );
}
