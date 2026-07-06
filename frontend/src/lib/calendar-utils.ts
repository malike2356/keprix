import type { CalendarEvent } from "@/lib/workspace-api";

export type CalendarViewMode = "month" | "week" | "day" | "schedule";

export const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export const HOUR_START = 6;
export const HOUR_END = 22;
export const HOURS = Array.from({ length: HOUR_END - HOUR_START + 1 }, (_, i) => i + HOUR_START);

export function startOfDay(date: Date): Date {
  const value = new Date(date);
  value.setHours(0, 0, 0, 0);
  return value;
}

export function endOfDay(date: Date): Date {
  const value = new Date(date);
  value.setHours(23, 59, 59, 999);
  return value;
}

export function addDays(date: Date, days: number): Date {
  const value = new Date(date);
  value.setDate(value.getDate() + days);
  return value;
}

export function startOfWeek(date: Date): Date {
  const value = startOfDay(date);
  const day = value.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  value.setDate(value.getDate() + diff);
  return value;
}

export function endOfWeek(date: Date): Date {
  return endOfDay(addDays(startOfWeek(date), 6));
}

export function startOfMonth(date: Date): Date {
  return startOfDay(new Date(date.getFullYear(), date.getMonth(), 1));
}

export function endOfMonth(date: Date): Date {
  return endOfDay(new Date(date.getFullYear(), date.getMonth() + 1, 0));
}

export function isSameDay(left: Date, right: Date): boolean {
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  );
}

export function isSameMonth(left: Date, right: Date): boolean {
  return left.getFullYear() === right.getFullYear() && left.getMonth() === right.getMonth();
}

export function isToday(date: Date): boolean {
  return isSameDay(date, new Date());
}

export function getMonthGrid(anchor: Date): Date[] {
  const start = startOfWeek(startOfMonth(anchor));
  return Array.from({ length: 42 }, (_, index) => addDays(start, index));
}

export function getWeekDays(anchor: Date): Date[] {
  const start = startOfWeek(anchor);
  return Array.from({ length: 7 }, (_, index) => addDays(start, index));
}

export function rangeForView(anchor: Date, mode: CalendarViewMode): { start: string; end: string } {
  let start: Date;
  let end: Date;

  switch (mode) {
    case "day":
      start = startOfDay(anchor);
      end = endOfDay(anchor);
      break;
    case "week":
      start = startOfWeek(anchor);
      end = endOfWeek(anchor);
      break;
    case "schedule":
      start = startOfDay(anchor);
      end = endOfDay(addDays(anchor, 30));
      break;
    default:
      start = startOfMonth(anchor);
      end = endOfMonth(anchor);
      break;
  }

  return { start: start.toISOString(), end: end.toISOString() };
}

export function labelForView(anchor: Date, mode: CalendarViewMode): string {
  switch (mode) {
    case "day":
      return anchor.toLocaleDateString(undefined, {
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric",
      });
    case "week": {
      const weekStart = startOfWeek(anchor);
      const weekEnd = endOfWeek(anchor);
      if (weekStart.getMonth() === weekEnd.getMonth()) {
        return `${weekStart.toLocaleDateString(undefined, { month: "long" })} ${weekStart.getDate()} - ${weekEnd.getDate()}, ${weekEnd.getFullYear()}`;
      }
      return `${weekStart.toLocaleDateString(undefined, { month: "short", day: "numeric" })} - ${weekEnd.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`;
    }
    case "schedule":
      return `Schedule from ${anchor.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" })}`;
    default:
      return anchor.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  }
}

export function shiftAnchor(anchor: Date, mode: CalendarViewMode, delta: number): Date {
  const value = new Date(anchor);
  switch (mode) {
    case "day":
      return addDays(value, delta);
    case "week":
      return addDays(value, delta * 7);
    case "schedule":
      return addDays(value, delta * 14);
    default:
      return new Date(value.getFullYear(), value.getMonth() + delta, 1);
  }
}

export function eventsForDay(events: CalendarEvent[], day: Date): CalendarEvent[] {
  const dayStart = startOfDay(day);
  const dayEnd = endOfDay(day);
  return events
    .filter((event) => {
      const start = new Date(event.start_at);
      const end = new Date(event.end_at);
      return start <= dayEnd && end >= dayStart;
    })
    .sort((left, right) => left.start_at.localeCompare(right.start_at));
}

export function formatEventTime(event: CalendarEvent): string {
  if (event.all_day) return "All day";
  const start = new Date(event.start_at);
  const end = new Date(event.end_at);
  return `${start.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })} - ${end.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`;
}

export function formatEventRange(event: CalendarEvent): string {
  const start = new Date(event.start_at);
  const end = new Date(event.end_at);
  if (event.all_day) {
    return start.toLocaleDateString();
  }
  return `${start.toLocaleString()} - ${end.toLocaleTimeString()}`;
}

export function eventPosition(
  event: CalendarEvent,
  day: Date,
): { top: number; height: number; hidden: boolean } {
  const dayStart = startOfDay(day);
  const gridStart = dayStart.getTime() + HOUR_START * 60 * 60 * 1000;
  const gridEnd = dayStart.getTime() + (HOUR_END + 1) * 60 * 60 * 1000;
  const start = Math.max(new Date(event.start_at).getTime(), gridStart);
  const end = Math.min(new Date(event.end_at).getTime(), gridEnd);

  if (end <= gridStart || start >= gridEnd) {
    return { top: 0, height: 0, hidden: true };
  }

  const total = gridEnd - gridStart;
  const top = ((start - gridStart) / total) * 100;
  const height = Math.max(((end - start) / total) * 100, 4);
  return { top, height, hidden: false };
}
