"use client";

import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import CalendarEventChip from "@/components/calendar/CalendarEventChip";
import { eventsForDay, formatEventTime, isToday, startOfDay } from "@/lib/calendar-utils";
import type { CalendarEvent } from "@/lib/workspace-api";

type CalendarScheduleViewProps = {
  anchor: Date;
  events: CalendarEvent[];
  onSelectEvent?: (event: CalendarEvent) => void;
};

export default function CalendarScheduleView({ anchor, events, onSelectEvent }: CalendarScheduleViewProps) {
  const days = Array.from({ length: 31 }, (_, index) => {
    const day = new Date(anchor);
    day.setDate(day.getDate() + index);
    return startOfDay(day);
  });

  const daysWithEvents = days
    .map((day) => ({ day, dayEvents: eventsForDay(events, day) }))
    .filter((entry) => entry.dayEvents.length > 0);

  if (!daysWithEvents.length) {
    return (
      <Box
        sx={{
          border: 1,
          borderColor: "divider",
          borderRadius: 1,
          p: 4,
          textAlign: "center",
          bgcolor: "background.paper",
        }}
      >
        <Typography variant="body2" color="text.secondary">
          No upcoming events in this range.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, overflow: "hidden", bgcolor: "background.paper" }}>
      {daysWithEvents.map(({ day, dayEvents }, index) => (
        <Box key={day.toISOString()}>
          {index > 0 ? <Divider /> : null}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "180px 1fr" }, gap: 2, p: 2 }}>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                {day.toLocaleDateString(undefined, { weekday: "long" })}
              </Typography>
              <Typography variant="body2" color={isToday(day) ? "primary.main" : "text.secondary"}>
                {day.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" })}
              </Typography>
            </Box>
            <Box sx={{ display: "grid", gap: 1 }}>
              {dayEvents.map((event) => (
                <Box
                  key={event.id}
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", md: "120px 1fr" },
                    gap: 1.5,
                    alignItems: "start",
                  }}
                >
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>
                    {formatEventTime(event)}
                  </Typography>
                  <Box onClick={() => onSelectEvent?.(event)} sx={{ cursor: onSelectEvent ? "pointer" : "default" }}>
                    <CalendarEventChip event={event} onClick={onSelectEvent} />
                    {event.location ? (
                      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                        {event.location}
                      </Typography>
                    ) : null}
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>
        </Box>
      ))}
    </Box>
  );
}
