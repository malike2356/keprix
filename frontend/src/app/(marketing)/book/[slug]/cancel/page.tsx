"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { useParams, useSearchParams } from "next/navigation";
import { cancelByGuestToken, fetchBookingByToken } from "@/lib/vical-api";

export default function CancelBookingPage() {
  const params = useParams<{ slug: string }>();
  const search = useSearchParams();
  const slug = params?.slug || "";
  const [token, setToken] = React.useState(search.get("token") || "");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (!token) return;
    void fetchBookingByToken(token)
      .then((b) => setMessage(`Loaded booking for ${b.guest_name} (${b.status})`))
      .catch(() => undefined);
  }, [token]);

  async function onCancel() {
    setBusy(true);
    setError(null);
    try {
      const booking = await cancelByGuestToken(token.trim());
      setMessage(`Cancelled. Status is now ${booking.status}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cancel failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 520, mx: "auto" }}>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Cancel booking
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Host link: /book/{slug}
      </Typography>
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      {message ? <Alert severity="info" sx={{ mb: 2 }}>{message}</Alert> : null}
      <Stack spacing={2}>
        <TextField label="Guest token" value={token} onChange={(e) => setToken(e.target.value)} fullWidth />
        <Button variant="contained" color="error" disabled={busy || !token.trim()} onClick={() => void onCancel()}>
          Cancel booking
        </Button>
      </Stack>
    </Box>
  );
}
