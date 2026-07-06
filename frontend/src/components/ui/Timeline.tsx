"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { SkeletonList } from "@/components/ui/loading";
import StatusPill from "@/components/ui/StatusPill";
import type { StatusKey } from "@/theme/tokens/status";

export type TimelineEvent = {
  id: string;
  title: string;
  description?: string;
  timestamp: string;
  status?: StatusKey;
};

type TimelineProps = {
  events: TimelineEvent[];
  loading?: boolean;
  emptyMessage?: string;
};

export default function Timeline({
  events,
  loading = false,
  emptyMessage = "No timeline events yet.",
}: TimelineProps) {
  if (loading) {
    return <SkeletonList rows={4} rowHeight={64} />;
  }
  if (events.length === 0) {
    return <Typography variant="body2" color="text.secondary">{emptyMessage}</Typography>;
  }

  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      {events.map((event, index) => (
        <Box key={event.id} sx={{ display: "grid", gridTemplateColumns: "16px 1fr", gap: 1.5 }}>
          <Box sx={{ position: "relative", display: "flex", justifyContent: "center" }}>
            <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: "primary.main", mt: 0.75 }} />
            {index < events.length - 1 ? (
              <Box sx={{ position: "absolute", top: 18, bottom: -16, width: 2, bgcolor: "divider" }} />
            ) : null}
          </Box>
          <Box>
            <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
              <Typography variant="subtitle2">{event.title}</Typography>
              {event.status ? <StatusPill status={event.status} /> : null}
            </Box>
            {event.description ? (
              <Typography variant="body2" color="text.secondary">{event.description}</Typography>
            ) : null}
            <Typography variant="caption" color="text.secondary">{event.timestamp}</Typography>
          </Box>
        </Box>
      ))}
    </Box>
  );
}
