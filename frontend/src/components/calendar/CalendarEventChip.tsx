"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { CalendarEvent } from "@/lib/workspace-api";
import { formatEventTime } from "@/lib/calendar-utils";

type CalendarEventChipProps = {
  event: CalendarEvent;
  compact?: boolean;
  onClick?: (event: CalendarEvent) => void;
};

export default function CalendarEventChip({ event, compact = false, onClick }: CalendarEventChipProps) {
  return (
    <Box
      onClick={() => onClick?.(event)}
      sx={{
        px: compact ? 0.75 : 1,
        py: compact ? 0.25 : 0.5,
        borderRadius: 0.75,
        bgcolor: "primary.main",
        color: "primary.contrastText",
        cursor: onClick ? "pointer" : "default",
        overflow: "hidden",
        "&:hover": onClick ? { filter: "brightness(1.05)" } : undefined,
      }}
    >
      <Typography variant="caption" sx={{ display: "block", fontWeight: 600, lineHeight: 1.2 }} noWrap>
        {event.title}
      </Typography>
      {!compact ? (
        <Typography variant="caption" sx={{ display: "block", opacity: 0.9, lineHeight: 1.2 }} noWrap>
          {formatEventTime(event)}
        </Typography>
      ) : null}
    </Box>
  );
}
