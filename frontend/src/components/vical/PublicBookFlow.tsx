"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { useParams, useSearchParams } from "next/navigation";
import {
  createPublicBooking,
  fetchPublicHost,
  fetchPublicIntake,
  fetchPublicSlots,
  publicIcsUrl,
  validatePublicIntake,
  type IntakePoolPublic,
  type VicalBooking,
  type VicalEventType,
  type VicalSlot,
} from "@/lib/vical-api";

type Step = "intake" | "slot" | "details" | "done" | "blocked";

export default function PublicBookFlow({ embed = false }: { embed?: boolean }) {
  const params = useParams<{ slug: string }>();
  const search = useSearchParams();
  const slug = params?.slug || "";
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [hostName, setHostName] = React.useState("Host");
  const [eventTypes, setEventTypes] = React.useState<VicalEventType[]>([]);
  const [eventTypeId, setEventTypeId] = React.useState<string>("");
  const [intake, setIntake] = React.useState<IntakePoolPublic | null>(null);
  const [answers, setAnswers] = React.useState<Record<string, string>>({});
  const [slots, setSlots] = React.useState<VicalSlot[]>([]);
  const [selectedSlot, setSelectedSlot] = React.useState<VicalSlot | null>(null);
  const [guestName, setGuestName] = React.useState("");
  const [guestEmail, setGuestEmail] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [step, setStep] = React.useState<Step>("slot");
  const [booking, setBooking] = React.useState<VicalBooking | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [blockMessage, setBlockMessage] = React.useState("");

  const selectedType = eventTypes.find((t) => t.id === eventTypeId) || eventTypes[0];

  React.useEffect(() => {
    if (!slug) return;
    void (async () => {
      setLoading(true);
      setError(null);
      try {
        const host = await fetchPublicHost(slug);
        setHostName(host.host.display_name);
        setEventTypes(host.event_types);
        const preferred =
          host.event_types.find((t) => t.slug === (search.get("type") || "consultation")) || host.event_types[0];
        setEventTypeId(preferred?.id || "");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Host not found");
      } finally {
        setLoading(false);
      }
    })();
  }, [slug, search]);

  React.useEffect(() => {
    if (!slug || !selectedType) return;
    void (async () => {
      try {
        const pool = await fetchPublicIntake(slug, { eventTypeId: selectedType.id, eventSlug: selectedType.slug });
        setIntake(pool);
        setStep(pool.required ? "intake" : "slot");
        if (!pool.required) {
          const offered = await fetchPublicSlots(slug, {
            eventTypeId: selectedType.id,
            eventSlug: selectedType.slug,
            count: 24,
          });
          setSlots(offered);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load booking options");
      }
    })();
  }, [slug, selectedType?.id]);

  async function submitIntake() {
    if (!selectedType) return;
    setBusy(true);
    setError(null);
    try {
      await validatePublicIntake(slug, {
        event_type_id: selectedType.id,
        event_type_slug: selectedType.slug,
        answers,
      });
      const offered = await fetchPublicSlots(slug, {
        eventTypeId: selectedType.id,
        eventSlug: selectedType.slug,
        count: 24,
      });
      setSlots(offered);
      setStep("slot");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Not eligible";
      if (message.toLowerCase().includes("eligible") || message.toLowerCase().includes("ready")) {
        setBlockMessage(message);
        setStep("blocked");
      } else {
        setError(message);
      }
    } finally {
      setBusy(false);
    }
  }

  async function submitBooking() {
    if (!selectedType || !selectedSlot) return;
    if (!guestName.trim() || !guestEmail.trim()) {
      setError("Name and email are required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await createPublicBooking(slug, {
        event_type_id: selectedType.id,
        event_type_slug: selectedType.slug,
        guest_name: guestName.trim(),
        guest_email: guestEmail.trim(),
        starts_at: selectedSlot.start_at,
        ends_at: selectedSlot.end_at,
        notes: notes.trim() || undefined,
        intake_answers: intake?.required ? answers : undefined,
      });
      setBooking(created);
      setStep("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not book");
    } finally {
      setBusy(false);
    }
  }

  const shellSx = embed
    ? { p: 2, maxWidth: 560, mx: "auto" }
    : { p: { xs: 2, md: 4 }, maxWidth: 640, mx: "auto" };

  return (
    <Box sx={shellSx}>
      {!embed ? (
        <Typography variant="h4" sx={{ mb: 0.5, fontWeight: 700 }}>
          Keprix
        </Typography>
      ) : null}
      <Typography variant={embed ? "h6" : "h5"} sx={{ mb: 0.5 }}>
        Book with {hostName}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Pick a time that works. You will get a confirmation based on the event type settings.
      </Typography>

      {loading ? <CircularProgress size={24} /> : null}
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}

      {!loading && eventTypes.length > 1 && step !== "done" && step !== "blocked" ? (
        <TextField
          select
          fullWidth
          size="small"
          label="Event type"
          value={eventTypeId}
          onChange={(e) => setEventTypeId(e.target.value)}
          sx={{ mb: 2 }}
        >
          {eventTypes.map((et) => (
            <MenuItem key={et.id} value={et.id}>
              {et.name} ({et.duration_minutes} min)
            </MenuItem>
          ))}
        </TextField>
      ) : null}

      {step === "blocked" ? (
        <Alert severity="info">{blockMessage || "You are not eligible for this booking."}</Alert>
      ) : null}

      {step === "intake" && intake?.pool ? (
        <Stack spacing={2}>
          <Typography variant="subtitle1">{intake.pool.name || "A few questions"}</Typography>
          {intake.pool.questions.map((q) => (
            <TextField
              key={q.id}
              label={q.label}
              select={q.type === "single_select"}
              required={q.required}
              value={answers[q.id] || ""}
              onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
              fullWidth
              size="small"
            >
              {q.type === "single_select"
                ? q.options.map((opt) => {
                    const value = typeof opt === "string" ? opt : opt.value;
                    const label = typeof opt === "string" ? opt : opt.label || opt.value;
                    return (
                      <MenuItem key={value} value={value}>
                        {label}
                      </MenuItem>
                    );
                  })
                : null}
            </TextField>
          ))}
          <Button variant="contained" disabled={busy} onClick={() => void submitIntake()}>
            Continue
          </Button>
        </Stack>
      ) : null}

      {step === "slot" ? (
        <Stack spacing={1}>
          <Typography variant="subtitle1">Available times</Typography>
          {slots.length === 0 ? (
            <Alert severity="info">No open slots in the next window. Try again later.</Alert>
          ) : (
            slots.map((slot) => (
              <Button
                key={slot.start_at}
                variant={selectedSlot?.start_at === slot.start_at ? "contained" : "outlined"}
                onClick={() => {
                  setSelectedSlot(slot);
                  setStep("details");
                }}
                sx={{ justifyContent: "flex-start" }}
              >
                {new Date(slot.start_at).toLocaleString()}
              </Button>
            ))
          )}
        </Stack>
      ) : null}

      {step === "details" && selectedSlot ? (
        <Stack spacing={2}>
          <Alert severity="info">Selected: {new Date(selectedSlot.start_at).toLocaleString()}</Alert>
          <TextField label="Your name" value={guestName} onChange={(e) => setGuestName(e.target.value)} required fullWidth />
          <TextField
            label="Email"
            type="email"
            value={guestEmail}
            onChange={(e) => setGuestEmail(e.target.value)}
            required
            fullWidth
          />
          <TextField label="Notes (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} fullWidth multiline minRows={2} />
          <Stack direction="row" spacing={1}>
            <Button onClick={() => setStep("slot")}>Back</Button>
            <Button variant="contained" disabled={busy} onClick={() => void submitBooking()}>
              Confirm request
            </Button>
          </Stack>
        </Stack>
      ) : null}

      {step === "done" && booking ? (
        <Stack spacing={1.5}>
          {booking.status === "confirmed" ? (
            <Alert severity="success">Booking confirmed.</Alert>
          ) : booking.status === "pending_review" ? (
            <Alert severity="info">Request received. The host will confirm shortly.</Alert>
          ) : booking.status === "pending_payment" ? (
            <Alert severity="warning">Deposit required before confirmation.</Alert>
          ) : (
            <Alert severity="info">Status: {booking.status}</Alert>
          )}
          <Typography variant="body2">
            {new Date(booking.starts_at).toLocaleString()} · token saved for cancel/reschedule
          </Typography>
          {booking.status === "confirmed" ? (
            <Button href={publicIcsUrl(booking.guest_token)} component="a">
              Download ICS
            </Button>
          ) : null}
          {booking.checkout?.checkout_url ? (
            <Button href={booking.checkout.checkout_url} component="a" variant="contained">
              Pay deposit
            </Button>
          ) : null}
          <Button href={`/book/${slug}/cancel?token=${encodeURIComponent(booking.guest_token)}`} component="a">
            Cancel booking
          </Button>
          <Button href={`/book/${slug}/reschedule?token=${encodeURIComponent(booking.guest_token)}`} component="a">
            Reschedule
          </Button>
        </Stack>
      ) : null}
    </Box>
  );
}
