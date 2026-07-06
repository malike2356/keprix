"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import {
  eventPosition,
  eventsForDay,
  formatEventTime,
  HOURS,
  isToday,
} from "@/lib/calendar-utils";
import type { CalendarEvent } from "@/lib/workspace-api";

type CalendarDayViewProps = {
  anchor: Date;
  events: CalendarEvent[];
  onSelectEvent?: (event: CalendarEvent) => void;
};

export default function CalendarDayView({ anchor, events, onSelectEvent }: CalendarDayViewProps) {
  const dayEvents = eventsForDay(events, anchor);
  const timedEvents = dayEvents.filter((event) => !event.all_day);
  const allDayEvents = dayEvents.filter((event) => event.all_day);

  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, overflow: "hidden", bgcolor: "background.paper" }}>
      <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: "divider", bgcolor: "action.hover" }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
          {anchor.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" })}
        </Typography>
        {isToday(anchor) ? (
          <Typography variant="caption" color="primary.main">
            Today
          </Typography>
        ) : null}
      </Box>

      {allDayEvents.length ? (
        <Box sx={{ px: 2, py: 1, borderBottom: 1, borderColor: "divider", display: "grid", gap: 0.75 }}>
          <Typography variant="caption" color="text.secondary">
            All day
          </Typography>
          {allDayEvents.map((event) => (
            <Box
              key={event.id}
              onClick={() => onSelectEvent?.(event)}
              sx={{
                px: 1,
                py: 0.75,
                borderRadius: 1,
                bgcolor: "secondary.main",
                color: "secondary.contrastText",
                cursor: "pointer",
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {event.title}
              </Typography>
            </Box>
          ))}
        </Box>
      ) : null}

      <Box sx={{ display: "grid", gridTemplateColumns: "72px 1fr", minHeight: 720 }}>
        <Box>
          {HOURS.map((hour) => (
            <Box
              key={hour}
              sx={{
                height: 48,
                borderBottom: 1,
                borderColor: "divider",
                px: 1,
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "flex-end",
              }}
            >
              <Typography variant="caption" color="text.secondary">
                {hour === 12 ? "12 PM" : hour < 12 ? `${hour} AM` : `${hour - 12} PM`}
              </Typography>
            </Box>
          ))}
        </Box>

        <Box sx={{ position: "relative", borderLeft: 1, borderColor: "divider" }}>
          {HOURS.map((hour) => (
            <Box key={hour} sx={{ height: 48, borderBottom: 1, borderColor: "action.hover" }} />
          ))}

          {timedEvents.map((event) => {
            const position = eventPosition(event, anchor);
            if (position.hidden) return null;
            return (
              <Box
                key={event.id}
                onClick={() => onSelectEvent?.(event)}
                sx={{
                  position: "absolute",
                  left: 8,
                  right: 8,
                  top: `${position.top}%`,
                  height: `${position.height}%`,
                  minHeight: 28,
                  px: 1,
                  py: 0.5,
                  borderRadius: 1,
                  bgcolor: "primary.main",
                  color: "primary.contrastText",
                  overflow: "hidden",
                  cursor: "pointer",
                  zIndex: 1,
                }}
              >
                <Typography variant="body2" sx={{ fontWeight: 700 }} noWrap>
                  {event.title}
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.9 }} noWrap>
                  {formatEventTime(event)}
                </Typography>
              </Box>
            );
          })}
        </Box>
      </Box>
    </Box>
  );
}
