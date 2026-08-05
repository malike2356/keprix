"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { useParams, useSearchParams } from "next/navigation";
import {
  fetchBookingByToken,
  fetchPublicSlots,
  rescheduleByGuestToken,
  type VicalSlot,
} from "@/lib/vical-api";

export default function RescheduleBookingPage() {
  const params = useParams<{ slug: string }>();
  const search = useSearchParams();
  const slug = params?.slug || "";
  const [token, setToken] = React.useState(search.get("token") || "");
  const [slots, setSlots] = React.useState<VicalSlot[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const [done, setDone] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (!slug) return;
    void fetchPublicSlots(slug, { count: 24 })
      .then(setSlots)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load slots"));
  }, [slug]);

  async function onPick(slot: VicalSlot) {
    setBusy(true);
    setError(null);
    try {
      await fetchBookingByToken(token.trim());
      const updated = await rescheduleByGuestToken(token.trim(), slot.start_at, slot.end_at);
      setDone(`Rescheduled to ${new Date(updated.starts_at).toLocaleString()}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reschedule failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 560, mx: "auto" }}>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Reschedule booking
      </Typography>
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      {done ? <Alert severity="success" sx={{ mb: 2 }}>{done}</Alert> : null}
      <TextField
        label="Guest token"
        value={token}
        onChange={(e) => setToken(e.target.value)}
        fullWidth
        sx={{ mb: 2 }}
      />
      <Stack spacing={1}>
        {slots.map((slot) => (
          <Button
            key={slot.start_at}
            variant="outlined"
            disabled={busy || !token.trim()}
            onClick={() => void onPick(slot)}
            sx={{ justifyContent: "flex-start" }}
          >
            {new Date(slot.start_at).toLocaleString()}
          </Button>
        ))}
      </Stack>
    </Box>
  );
}
