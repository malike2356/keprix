"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import {
  createOutreachBooking,
  fetchOutreachBookings,
  fetchOutreachLeads,
  updateOutreachBookingStatus,
} from "@/lib/outreach-api";

const WORKSPACE = "default";

const STATUS_ACTIONS = ["confirmed", "cancelled", "no_show", "attended", "rescheduled"] as const;

export default function OutreachBookingsPage() {
  const [leadId, setLeadId] = React.useState("");
  const [startsAt, setStartsAt] = React.useState("");
  const [endsAt, setEndsAt] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const leads = useSWR(["outreach-leads", WORKSPACE], () => fetchOutreachLeads(WORKSPACE));
  const bookings = useSWR(["outreach-bookings", WORKSPACE], () => fetchOutreachBookings(WORKSPACE));

  React.useEffect(() => {
    const first = leads.data?.leads?.[0]?.id;
    if (!leadId && first) setLeadId(first);
  }, [leads.data, leadId]);

  const onCreate = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!leadId) throw new Error("Pick a lead first");
      if (!startsAt) throw new Error("Start time is required");
      await createOutreachBooking(
        {
          lead_id: leadId,
          starts_at: new Date(startsAt).toISOString(),
          ends_at: endsAt ? new Date(endsAt).toISOString() : undefined,
          notes: notes.trim() || undefined,
          status: "scheduled",
        },
        WORKSPACE,
      );
      setStartsAt("");
      setEndsAt("");
      setNotes("");
      setMessage("Booking created; confirmation awaits Soft Wall where configured");
      await bookings.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create booking");
    } finally {
      setBusy(false);
    }
  };

  const onStatus = async (bookingId: string, status: string) => {
    setBusy(true);
    setError(null);
    try {
      await updateOutreachBookingStatus(bookingId, status, WORKSPACE);
      setMessage(`Booking marked ${status.replace(/_/g, " ")}`);
      await bookings.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update booking");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Typography variant="body2" color="text.secondary">
        Prefer <Link href="/vical">viCal</Link> as booking source of truth when a host profile exists. Soft Wall rows
        link via notes containing vical:booking_id and mesh to CRM/Outreach/Calendar. Creating Soft Wall-only bookings
        here is a fallback when viCal host is missing.
      </Typography>
      <Alert severity="info">
        Open mesh: <Link href="/vical">viCal hub</Link> · <Link href="/calendar">Calendar</Link> ·{" "}
        <Link href="/crm">CRM</Link>
      </Alert>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            New booking
          </Typography>
          <Stack spacing={1.5}>
            <FormControl size="small" fullWidth>
              <InputLabel id="booking-lead">Lead</InputLabel>
              <Select labelId="booking-lead" label="Lead" value={leadId} onChange={(e) => setLeadId(e.target.value)}>
                {(leads.data?.leads ?? []).map((lead) => (
                  <MenuItem key={lead.id} value={lead.id}>
                    {lead.name}
                    {lead.email ? ` (${lead.email})` : ""}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <TextField
                size="small"
                fullWidth
                label="Starts at"
                type="datetime-local"
                InputLabelProps={{ shrink: true }}
                value={startsAt}
                onChange={(e) => setStartsAt(e.target.value)}
              />
              <TextField
                size="small"
                fullWidth
                label="Ends at"
                type="datetime-local"
                InputLabelProps={{ shrink: true }}
                value={endsAt}
                onChange={(e) => setEndsAt(e.target.value)}
              />
            </Stack>
            <TextField size="small" fullWidth label="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
            <Button size="small" variant="contained" disabled={busy} onClick={() => void onCreate()} sx={{ alignSelf: "flex-start" }}>
              Create booking
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {bookings.isLoading && !bookings.data ? (
        <Typography color="text.secondary">Loading bookings...</Typography>
      ) : (bookings.data?.bookings ?? []).length === 0 ? (
        <Typography color="text.secondary">No bookings yet.</Typography>
      ) : (
        <Stack spacing={1}>
          {(bookings.data?.bookings ?? []).map((booking) => {
            const leadRef = booking.lead_id || booking.leadId;
            const start = booking.starts_at || booking.startsAt;
            return (
              <Card key={booking.id} variant="outlined">
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" spacing={1} flexWrap="wrap" useFlexGap>
                    <Typography variant="body2" fontWeight={600}>
                      {booking.status}
                      {start ? ` · ${new Date(start).toLocaleString()}` : ""}
                    </Typography>
                    {leadRef ? (
                      <Button size="small" component={Link} href={`/outreach/leads/${leadRef}`}>
                        Open lead
                      </Button>
                    ) : null}
                  </Stack>
                  {(booking.attendee_name || booking.attendee_email || booking.notes) && (
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                      {[booking.attendee_name, booking.attendee_email, booking.notes].filter(Boolean).join(" · ")}
                    </Typography>
                  )}
                  <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }}>
                    {STATUS_ACTIONS.map((status) => (
                      <Button
                        key={status}
                        size="small"
                        variant="outlined"
                        disabled={busy}
                        onClick={() => void onStatus(booking.id, status)}
                      >
                        {status.replace(/_/g, " ")}
                      </Button>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Stack>
      )}
    </Stack>
  );
}
