"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import * as React from "react";
import CalendarDayView from "@/components/calendar/CalendarDayView";
import CalendarMonthView from "@/components/calendar/CalendarMonthView";
import CalendarScheduleView from "@/components/calendar/CalendarScheduleView";
import CalendarWeekView from "@/components/calendar/CalendarWeekView";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonList } from "@/components/ui/loading";
import {
  formatEventRange,
  labelForView,
  rangeForView,
  shiftAnchor,
  type CalendarViewMode,
} from "@/lib/calendar-utils";
import { createCalendarEvent, fetchCalendarEvents, type CalendarEvent } from "@/lib/workspace-api";

const VIEW_TABS: Array<{ value: CalendarViewMode; label: string }> = [
  { value: "month", label: "Month" },
  { value: "week", label: "Week" },
  { value: "day", label: "Day" },
  { value: "schedule", label: "Schedule" },
];

export default function CalendarPage() {
  const [anchor, setAnchor] = React.useState(() => new Date());
  const [view, setView] = React.useState<CalendarViewMode>("month");
  const [events, setEvents] = React.useState<CalendarEvent[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [selectedEvent, setSelectedEvent] = React.useState<CalendarEvent | null>(null);
  const [title, setTitle] = React.useState("");
  const [startAt, setStartAt] = React.useState("");
  const [endAt, setEndAt] = React.useState("");
  const [saving, setSaving] = React.useState(false);

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
    load();
  }, [load]);

  function shift(delta: number) {
    setAnchor((prev) => shiftAnchor(prev, view, delta));
  }

  function openCreateDialog(day?: Date) {
    const base = day ? new Date(day) : new Date(anchor);
    base.setHours(9, 0, 0, 0);
    const end = new Date(base);
    end.setHours(10, 0, 0, 0);
    setTitle("");
    setStartAt(toLocalInputValue(base));
    setEndAt(toLocalInputValue(end));
    setDialogOpen(true);
  }

  async function handleCreate() {
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

  return (
    <Box>
      <PageHeader
        title="Calendar"
        description="Monthly, weekly, daily, and schedule views for your workspace events."
        breadcrumbs={[
          { label: "Workspace", href: "/launcher" },
          { label: "Calendar", href: "/calendar" },
        ]}
        actions={
          <Button variant="contained" onClick={() => openCreateDialog()}>
            New event
          </Button>
        }
      />

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
          description="Add events manually or connect CalDAV sync from settings."
          icon={<CalendarMonthIcon sx={{ fontSize: 48 }} />}
          actionLabel="New event"
          onAction={() => openCreateDialog()}
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
            <CalendarWeekView anchor={anchor} events={events} onSelectEvent={setSelectedEvent} />
          ) : null}
          {view === "day" ? (
            <CalendarDayView anchor={anchor} events={events} onSelectEvent={setSelectedEvent} />
          ) : null}
          {view === "schedule" ? (
            <CalendarScheduleView anchor={anchor} events={events} onSelectEvent={setSelectedEvent} />
          ) : null}
        </>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New event</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
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
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={saving || !title.trim()}>
            Create
          </Button>
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
            </DialogContent>
            <DialogActions>
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
