"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { calendarEventHoverSx } from "@/components/calendar/calendar-motion";
import {
  eventPosition,
  eventsForDay,
  getWeekDays,
  HOUR_END,
  HOURS,
  isToday,
  WEEKDAY_LABELS,
} from "@/lib/calendar-utils";
import type { CalendarEvent } from "@/lib/workspace-api";

type CalendarWeekViewProps = {
  anchor: Date;
  events: CalendarEvent[];
  onSelectEvent?: (event: CalendarEvent) => void;
  onSelectSlot?: (day: Date, hour: number) => void;
};

export default function CalendarWeekView({ anchor, events, onSelectEvent, onSelectSlot }: CalendarWeekViewProps) {
  const days = getWeekDays(anchor);

  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, overflow: "auto", bgcolor: "background.paper" }}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "56px repeat(7, minmax(120px, 1fr))",
          borderBottom: 1,
          borderColor: "divider",
          bgcolor: "action.hover",
          position: "sticky",
          top: 0,
          zIndex: 2,
        }}
      >
        <Box />
        {days.map((day, index) => (
          <Box key={day.toISOString()} sx={{ px: 1, py: 1, textAlign: "center" }}>
            <Typography variant="caption" color="text.secondary" display="block">
              {WEEKDAY_LABELS[index]}
            </Typography>
            <Typography
              variant="body2"
              sx={{
                fontWeight: isToday(day) ? 700 : 500,
                color: isToday(day) ? "primary.main" : "text.primary",
              }}
            >
              {day.getDate()}
            </Typography>
          </Box>
        ))}
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: "56px repeat(7, minmax(120px, 1fr))", minHeight: 720 }}>
        <Box>
          {HOURS.map((hour) => (
            <Box
              key={hour}
              sx={{
                height: 48,
                borderBottom: 1,
                borderColor: "divider",
                px: 0.5,
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

        {days.map((day) => {
          const dayEvents = eventsForDay(events, day).filter((event) => !event.all_day);
          const allDayEvents = eventsForDay(events, day).filter((event) => event.all_day);

          return (
            <Box key={day.toISOString()} sx={{ position: "relative", borderLeft: 1, borderColor: "divider" }}>
              {allDayEvents.length ? (
                <Box sx={{ borderBottom: 1, borderColor: "divider", p: 0.5, display: "grid", gap: 0.5 }}>
                  {allDayEvents.map((event) => (
                    <Box
                      key={event.id}
                      onClick={() => onSelectEvent?.(event)}
                      sx={{
                        px: 0.75,
                        py: 0.25,
                        borderRadius: 0.75,
                        bgcolor: "secondary.main",
                        color: "secondary.contrastText",
                        cursor: "pointer",
                        typography: "caption",
                        fontWeight: 600,
                        ...calendarEventHoverSx,
                      }}
                    >
                      {event.title}
                    </Box>
                  ))}
                </Box>
              ) : null}

              <Box sx={{ position: "relative", height: HOURS.length * 48 }}>
                {HOURS.map((hour) => (
                  <Box
                    key={hour}
                    onClick={() => onSelectSlot?.(day, hour)}
                    sx={{
                      height: 48,
                      borderBottom: 1,
                      borderColor: hour === HOUR_END ? "divider" : "action.hover",
                      cursor: onSelectSlot ? "pointer" : "default",
                      "&:hover": onSelectSlot ? { bgcolor: "action.hover" } : undefined,
                    }}
                  />
                ))}

                {dayEvents.map((event) => {
                  const position = eventPosition(event, day);
                  if (position.hidden) return null;
                  return (
                    <Box
                      key={event.id}
                      onClick={() => onSelectEvent?.(event)}
                      sx={{
                        position: "absolute",
                        left: 4,
                        right: 4,
                        top: `${position.top}%`,
                        height: `${position.height}%`,
                        minHeight: 20,
                        px: 0.75,
                        py: 0.25,
                        borderRadius: 0.75,
                        bgcolor: "primary.main",
                        color: "primary.contrastText",
                        overflow: "hidden",
                        cursor: "pointer",
                        zIndex: 1,
                        ...calendarEventHoverSx,
                      }}
                    >
                      <Typography variant="caption" sx={{ fontWeight: 700, display: "block" }} noWrap>
                        {event.title}
                      </Typography>
                    </Box>
                  );
                })}
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
