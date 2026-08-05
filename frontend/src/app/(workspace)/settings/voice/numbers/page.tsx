"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

export default function VoiceNumbersPage() {
  const [baseUrl, setBaseUrl] = React.useState("");
  const [plan, setPlan] = React.useState<Record<string, string> | null>(null);

  async function loadPlan() {
    const response = await ceApi("/api/voice/phone/provision/twilio", {
      method: "POST",
      body: JSON.stringify({ base_url: baseUrl || "https://core.keprix.ai", country: "GB" }),
    });
    if (response.ok) setPlan((await response.json()) as Record<string, string>);
  }

  return (
    <Box>
      <PageHeader title="Phone numbers" description="Twilio webhook and media stream configuration for Aiva receptionist numbers." />
      <Stack spacing={2}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <TextField label="Public base URL" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} fullWidth size="small" />
            <Button variant="contained" onClick={loadPlan}>
              Generate
            </Button>
          </Stack>
        </Paper>
        {plan ? (
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Stack spacing={1}>
              <Typography variant="body2">
                <strong>Voice webhook:</strong> {plan.voice_webhook}
              </Typography>
              <Typography variant="body2">
                <strong>Status callback:</strong> {plan.status_callback}
              </Typography>
              <Typography variant="body2">
                <strong>Media stream:</strong> {plan.media_stream}
              </Typography>
            </Stack>
          </Paper>
        ) : null}
      </Stack>
    </Box>
  );
}
