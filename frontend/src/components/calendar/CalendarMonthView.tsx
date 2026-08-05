"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import CalendarEventChip from "@/components/calendar/CalendarEventChip";
import { calendarDayHoverSx, calendarDayNumberSx } from "@/components/calendar/calendar-motion";
import {
  eventsForDay,
  getMonthGrid,
  isSameMonth,
  isToday,
  WEEKDAY_LABELS,
} from "@/lib/calendar-utils";
import type { CalendarEvent } from "@/lib/workspace-api";

type CalendarMonthViewProps = {
  anchor: Date;
  events: CalendarEvent[];
  onSelectEvent?: (event: CalendarEvent) => void;
  onSelectDay?: (day: Date) => void;
};

export default function CalendarMonthView({ anchor, events, onSelectEvent, onSelectDay }: CalendarMonthViewProps) {
  const cells = getMonthGrid(anchor);

  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, overflow: "visible", bgcolor: "background.paper" }}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          borderBottom: 1,
          borderColor: "divider",
          bgcolor: "action.hover",
        }}
      >
        {WEEKDAY_LABELS.map((label) => (
          <Box key={label} sx={{ px: 1, py: 1 }}>
            <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary" }}>
              {label}
            </Typography>
          </Box>
        ))}
      </Box>
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)" }}>
        {cells.map((day) => {
          const dayEvents = eventsForDay(events, day);
          const inMonth = isSameMonth(day, anchor);
          const today = isToday(day);

          return (
            <Box
              key={day.toISOString()}
              onClick={() => onSelectDay?.(day)}
              sx={{
                minHeight: 108,
                borderRight: 1,
                borderBottom: 1,
                borderColor: "divider",
                p: 0.75,
                bgcolor: inMonth ? "background.paper" : "action.hover",
                cursor: onSelectDay ? "pointer" : "default",
                position: "relative",
                ...calendarDayHoverSx,
              }}
            >
              <Typography
                className="calendar-day-number"
                variant="caption"
                sx={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  fontWeight: today ? 700 : 500,
                  bgcolor: today ? "primary.main" : "transparent",
                  color: today ? "primary.contrastText" : inMonth ? "text.primary" : "text.secondary",
                  mb: 0.5,
                  ...calendarDayNumberSx,
                }}
              >
                {day.getDate()}
              </Typography>
              <Box sx={{ display: "grid", gap: 0.5 }}>
                {dayEvents.slice(0, 3).map((event) => (
                  <CalendarEventChip key={event.id} event={event} compact onClick={onSelectEvent} />
                ))}
                {dayEvents.length > 3 ? (
                  <Typography variant="caption" color="text.secondary">
                    +{dayEvents.length - 3} more
                  </Typography>
                ) : null}
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
