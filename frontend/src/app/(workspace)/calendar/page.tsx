"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import CalendarDayView from "@/components/calendar/CalendarDayView";
import CalendarMonthView from "@/components/calendar/CalendarMonthView";
import CalendarScheduleView from "@/components/calendar/CalendarScheduleView";
import CalendarSyncPanel from "@/components/calendar/CalendarSyncPanel";
import CalendarWeekView from "@/components/calendar/CalendarWeekView";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonList } from "@/components/ui/loading";
import MeshRelatedLinks, { buildVicalRelatedLinks } from "@/components/vical/MeshRelatedLinks";
import {
  formatEventRange,
  labelForView,
  rangeForView,
  shiftAnchor,
  type CalendarViewMode,
} from "@/lib/calendar-utils";
import { createHostBooking, fetchEventTypes, type VicalEventType } from "@/lib/vical-api";
import {
  contactIdFromEvent,
  createCalendarEvent,
  fetchCalendarEvent,
  fetchCalendarEvents,
  vicalBookingIdFromEvent,
  type CalendarEvent,
} from "@/lib/workspace-api";

const VIEW_TABS: Array<{ value: CalendarViewMode; label: string }> = [
  { value: "month", label: "Month" },
  { value: "week", label: "Week" },
  { value: "day", label: "Day" },
  { value: "schedule", label: "Schedule" },
];

type CreateMode = "event" | "booking";

export default function CalendarPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const eventParam = searchParams.get("event");

  const [anchor, setAnchor] = React.useState(() => new Date());
  const [view, setView] = React.useState<CalendarViewMode>("month");
  const [events, setEvents] = React.useState<CalendarEvent[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [createMode, setCreateMode] = React.useState<CreateMode>("event");
  const [selectedEvent, setSelectedEvent] = React.useState<CalendarEvent | null>(null);
  const [title, setTitle] = React.useState("");
  const [startAt, setStartAt] = React.useState("");
  const [endAt, setEndAt] = React.useState("");
  const [guestName, setGuestName] = React.useState("");
  const [guestEmail, setGuestEmail] = React.useState("");
  const [eventTypes, setEventTypes] = React.useState<VicalEventType[]>([]);
  const [eventTypeId, setEventTypeId] = React.useState("");
  const [saving, setSaving] = React.useState(false);
  const focusedEventRef = React.useRef<string | null>(null);

  const range = React.useMemo(() => rangeForView(anchor, view), [anchor, view]);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEvents(await fetchCalendarEvents(range.start, range.end));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load events");
    } finally {
      setLoading(false);
    }
  }, [range.end, range.start]);

  React.useEffect(() => {
    void load();
  }, [load]);

  React.useEffect(() => {
    if (!eventParam) {
      focusedEventRef.current = null;
      return;
    }
    if (focusedEventRef.current === eventParam) return;

    let cancelled = false;
    async function focusEvent() {
      const fromList = events.find((row) => row.id === eventParam);
      let target = fromList;
      if (!target) {
        try {
          target = await fetchCalendarEvent(eventParam);
        } catch {
          if (!cancelled) setError(`Event not found: ${eventParam}`);
          return;
        }
      }
      if (cancelled || !target) return;
      focusedEventRef.current = eventParam;
      const start = new Date(target.start_at);
      if (!Number.isNaN(start.getTime())) {
        setAnchor(start);
        setView("day");
      }
      setSelectedEvent(target);
      setEvents((prev) => (prev.some((row) => row.id === target!.id) ? prev : [...prev, target!]));
    }
    void focusEvent();
    return () => {
      cancelled = true;
    };
  }, [eventParam, events]);

  function shift(delta: number) {
    setAnchor((prev) => shiftAnchor(prev, view, delta));
  }

  function openCreateDialog(opts?: { day?: Date; hour?: number; mode?: CreateMode }) {
    const mode = opts?.mode ?? "event";
    const base = opts?.day ? new Date(opts.day) : new Date(anchor);
    if (typeof opts?.hour === "number") {
      base.setHours(opts.hour, 0, 0, 0);
    } else {
      base.setHours(9, 0, 0, 0);
    }
    const end = new Date(base);
    end.setHours(base.getHours() + 1, base.getMinutes(), 0, 0);
    setCreateMode(mode);
    setTitle("");
    setGuestName("");
    setGuestEmail("");
    setStartAt(toLocalInputValue(base));
    setEndAt(toLocalInputValue(end));
    setDialogOpen(true);
    if (mode === "booking") {
      void ensureEventTypes();
    }
  }

  async function ensureEventTypes() {
    if (eventTypes.length) return;
    try {
      const rows = await fetchEventTypes();
      const active = rows.filter((row) => row.active !== false);
      setEventTypes(active);
      if (!eventTypeId && active[0]) setEventTypeId(active[0].id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load event types");
    }
  }

  React.useEffect(() => {
    if (!dialogOpen || createMode !== "booking") return;
    const selected = eventTypes.find((row) => row.id === eventTypeId);
    if (!selected || !startAt) return;
    const start = new Date(startAt);
    if (Number.isNaN(start.getTime())) return;
    const end = new Date(start.getTime() + selected.duration_minutes * 60_000);
    setEndAt(toLocalInputValue(end));
    // Only adjust end when type or start changes while in booking mode.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventTypeId, createMode]);

  async function handleCreateEvent() {
    if (!title.trim() || !startAt || !endAt) return;
    setSaving(true);
    try {
      const event = await createCalendarEvent({
        title: title.trim(),
        start_at: new Date(startAt).toISOString(),
        end_at: new Date(endAt).toISOString(),
      });
      setEvents((prev) => [...prev, event].sort((left, right) => left.start_at.localeCompare(right.start_at)));
      setDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create event");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateBooking() {
    if (!guestName.trim() || !guestEmail.trim() || !startAt || !eventTypeId) return;
    setSaving(true);
    setError(null);
    try {
      const booking = await createHostBooking({
        guest_name: guestName.trim(),
        guest_email: guestEmail.trim(),
        starts_at: new Date(startAt).toISOString(),
        ends_at: endAt ? new Date(endAt).toISOString() : undefined,
        event_type_id: eventTypeId,
        skip_slot_check: true,
      });
      setDialogOpen(false);
      await load();
      if (booking.workspace_event_id) {
        router.push(`/calendar?event=${encodeURIComponent(booking.workspace_event_id)}`);
      } else {
        router.push(`/vical?booking=${encodeURIComponent(booking.id)}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create booking");
    } finally {
      setSaving(false);
    }
  }

  const selectedBookingId = selectedEvent ? vicalBookingIdFromEvent(selectedEvent) : null;
  const selectedContactId = selectedEvent ? contactIdFromEvent(selectedEvent) : null;

  return (
    <Box>
      <PageHeader
        title="Calendar"
        description="Monthly, weekly, daily, and schedule views for your workspace events."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Calendar", href: "/calendar" },
        ]}
        actions={
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <Button variant="outlined" onClick={() => openCreateDialog({ mode: "booking" })}>
              New booking
            </Button>
            <Button variant="contained" onClick={() => openCreateDialog({ mode: "event" })}>
              New event
            </Button>
          </Box>
        }
      />

      <Box sx={{ mb: 2 }}>
        <CalendarSyncPanel onSynced={() => void load()} />
      </Box>

      <Box
        sx={{
          display: "flex",
          alignItems: { xs: "stretch", md: "center" },
          justifyContent: "space-between",
          gap: 2,
          mb: 2,
          flexWrap: "wrap",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          <Button size="small" variant="outlined" onClick={() => setAnchor(new Date())}>
            Today
          </Button>
          <IconButtonRow onPrev={() => shift(-1)} onNext={() => shift(1)} />
          <Typography sx={{ fontWeight: 600, minWidth: 180 }}>{labelForView(anchor, view)}</Typography>
        </Box>
        <Tabs
          value={view}
          onChange={(_, value: CalendarViewMode) => setView(value)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ minHeight: 40 }}
        >
          {VIEW_TABS.map((tab) => (
            <Tab key={tab.value} value={tab.value} label={tab.label} sx={{ minHeight: 40, py: 0.5 }} />
          ))}
        </Tabs>
      </Box>

      {error ? (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      ) : null}

      {loading ? (
        <SkeletonList rows={6} rowHeight={56} />
      ) : !events.length && view === "schedule" ? (
        <EmptyState
          title="No events"
          description="Add events manually, book with viCal, or connect Google, iCloud, Nextcloud, or any CalDAV/ICS calendar with Sync calendars."
          icon={<CalendarMonthIcon sx={{ fontSize: 48 }} />}
          actionLabel="New event"
          onAction={() => openCreateDialog({ mode: "event" })}
        />
      ) : (
        <>
          {view === "month" ? (
            <CalendarMonthView
              anchor={anchor}
              events={events}
              onSelectEvent={setSelectedEvent}
              onSelectDay={(day) => {
                setAnchor(day);
                setView("day");
              }}
            />
          ) : null}
          {view === "week" ? (
            <CalendarWeekView
              anchor={anchor}
              events={events}
              onSelectEvent={setSelectedEvent}
              onSelectSlot={(day, hour) => openCreateDialog({ day, hour, mode: "booking" })}
            />
          ) : null}
          {view === "day" ? (
            <CalendarDayView
              anchor={anchor}
              events={events}
              onSelectEvent={setSelectedEvent}
              onSelectSlot={(day, hour) => openCreateDialog({ day, hour, mode: "booking" })}
            />
          ) : null}
          {view === "schedule" ? (
            <CalendarScheduleView anchor={anchor} events={events} onSelectEvent={setSelectedEvent} />
          ) : null}
        </>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{createMode === "booking" ? "New booking" : "New event"}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <Tabs
            value={createMode}
            onChange={(_, value: CreateMode) => {
              setCreateMode(value);
              if (value === "booking") void ensureEventTypes();
            }}
            sx={{ minHeight: 36, mb: 1 }}
          >
            <Tab value="event" label="Event" sx={{ minHeight: 36 }} />
            <Tab value="booking" label="Booking" sx={{ minHeight: 36 }} />
          </Tabs>
          {createMode === "event" ? (
            <>
              <TextField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
              <TextField
                label="Start"
                type="datetime-local"
                value={startAt}
                onChange={(e) => setStartAt(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
              <TextField
                label="End"
                type="datetime-local"
                value={endAt}
                onChange={(e) => setEndAt(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </>
          ) : (
            <>
              <FormControl fullWidth>
                <InputLabel id="calendar-booking-type">Event type</InputLabel>
                <Select
                  labelId="calendar-booking-type"
                  label="Event type"
                  value={eventTypeId}
                  onChange={(e) => setEventTypeId(String(e.target.value))}
                >
                  {eventTypes.map((et) => (
                    <MenuItem key={et.id} value={et.id}>
                      {et.name} ({et.duration_minutes}m)
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                label="Guest name"
                value={guestName}
                onChange={(e) => setGuestName(e.target.value)}
                autoFocus
              />
              <TextField
                label="Guest email"
                type="email"
                value={guestEmail}
                onChange={(e) => setGuestEmail(e.target.value)}
              />
              <TextField
                label="Start"
                type="datetime-local"
                value={startAt}
                onChange={(e) => setStartAt(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
              <TextField
                label="End"
                type="datetime-local"
                value={endAt}
                onChange={(e) => setEndAt(e.target.value)}
                InputLabelProps={{ shrink: true }}
                helperText="Defaults to the event type duration from start."
              />
              <Typography variant="caption" color="text.secondary">
                Creates a viCal booking. Confirmed bookings appear on this calendar with an Open booking link.
              </Typography>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          {createMode === "event" ? (
            <Button variant="contained" onClick={() => void handleCreateEvent()} disabled={saving || !title.trim()}>
              Create
            </Button>
          ) : (
            <Button
              variant="contained"
              onClick={() => void handleCreateBooking()}
              disabled={saving || !guestName.trim() || !guestEmail.trim() || !eventTypeId}
            >
              Create booking
            </Button>
          )}
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(selectedEvent)} onClose={() => setSelectedEvent(null)} fullWidth maxWidth="sm">
        {selectedEvent ? (
          <>
            <DialogTitle>{selectedEvent.title}</DialogTitle>
            <DialogContent sx={{ display: "grid", gap: 1 }}>
              <Typography variant="body2" color="text.secondary">
                {formatEventRange(selectedEvent)}
              </Typography>
              {selectedEvent.location ? (
                <Typography variant="body2" color="text.secondary">
                  Location: {selectedEvent.location}
                </Typography>
              ) : null}
              {selectedEvent.description ? (
                <Typography variant="body2">{selectedEvent.description}</Typography>
              ) : null}
              {selectedEvent.caldav_source_id ? (
                <Typography variant="caption" color="text.secondary">
                  Synced from external calendar
                  {selectedEvent.external_readonly ? " (read-only)" : ""}
                </Typography>
              ) : null}
              {selectedContactId ? (
                <>
                  <Typography variant="subtitle2" sx={{ mt: 1 }}>
                    Related
                  </Typography>
                  <MeshRelatedLinks
                    links={buildVicalRelatedLinks({
                      contactId: selectedContactId,
                    })}
                  />
                </>
              ) : null}
            </DialogContent>
            <DialogActions>
              {selectedBookingId ? (
                <Button
                  variant="contained"
                  href={`/vical?booking=${encodeURIComponent(selectedBookingId)}`}
                  component="a"
                >
                  Open booking
                </Button>
              ) : null}
              <Button onClick={() => setSelectedEvent(null)}>Close</Button>
            </DialogActions>
          </>
        ) : null}
      </Dialog>
    </Box>
  );
}

function IconButtonRow({ onPrev, onNext }: { onPrev: () => void; onNext: () => void }) {
  return (
    <Box sx={{ display: "inline-flex", border: 1, borderColor: "divider", borderRadius: 1, overflow: "hidden" }}>
      <Button size="small" onClick={onPrev} sx={{ minWidth: 36, px: 0.5, borderRadius: 0 }}>
        <ChevronLeftIcon fontSize="small" />
      </Button>
      <Button size="small" onClick={onNext} sx={{ minWidth: 36, px: 0.5, borderRadius: 0 }}>
        <ChevronRightIcon fontSize="small" />
      </Button>
    </Box>
  );
}

function toLocalInputValue(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
