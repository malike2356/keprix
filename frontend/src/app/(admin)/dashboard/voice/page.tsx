"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageContainer from "@/components/shared/PageContainer";
import { ceApi } from "@/lib/ce-api";
import { useRequireAdmin } from "@/lib/ce-auth";

type VoiceSession = {
  session_id: string;
  caller: string;
  called: string;
  status: string;
  topic: string;
  started_at: string;
  escalated: boolean;
  appointments_booked: number;
};

async function fetchSessions(): Promise<VoiceSession[]> {
  const response = await ceApi("/api/voice/phone/sessions");
  if (!response.ok) throw new Error("Failed to load phone sessions");
  const payload = (await response.json()) as { sessions: VoiceSession[] };
  return payload.sessions;
}

async function fetchCost(): Promise<{ total_usd: number; stt_usd: number; tts_usd: number; twilio_usd: number }> {
  const response = await ceApi("/api/voice/phone/cost-estimate?seconds=300");
  if (!response.ok) throw new Error("Failed to load call cost estimate");
  return response.json();
}

export default function AdminVoicePage() {
  useRequireAdmin();
  const { data: sessions, error, mutate } = useSWR("admin-phone-sessions", fetchSessions);
  const { data: cost } = useSWR("admin-phone-cost", fetchCost);
  const active = (sessions || []).filter((session) => session.status === "connected").length;

  return (
    <PageContainer title="Aiva phone receptionist" description="Inbound Twilio calls, live sessions, escalation, booking, and cost controls." padded={false}>
      <Box sx={{ display: "grid", gap: 2 }}>
        {error ? <Alert severity="error">Failed to load Aiva phone sessions.</Alert> : null}
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ xs: "flex-start", sm: "center" }}>
            <Chip color={active ? "success" : "default"} label={`${active} active`} />
            <Chip variant="outlined" label={`${sessions?.length ?? 0} total calls`} />
            <Chip variant="outlined" color={(cost?.total_usd ?? 1) < 0.2 ? "success" : "warning"} label={`5 min estimate $${(cost?.total_usd ?? 0).toFixed(3)}`} />
            <Box sx={{ flex: 1 }} />
            <Button variant="outlined" size="small" onClick={() => mutate()}>
              Refresh
            </Button>
          </Stack>
        </Paper>
        <Paper variant="outlined" sx={{ overflow: "hidden" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Started</TableCell>
                <TableCell>Caller</TableCell>
                <TableCell>Number</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Outcome</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(sessions || []).map((session) => (
                <TableRow key={session.session_id}>
                  <TableCell>{new Date(session.started_at).toLocaleString()}</TableCell>
                  <TableCell>{session.caller || "Unknown"}</TableCell>
                  <TableCell>{session.called || "Unassigned"}</TableCell>
                  <TableCell>
                    <Chip size="small" color={session.status === "connected" ? "success" : "default"} label={session.status} />
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      {session.escalated ? <Chip size="small" color="warning" label="Escalated" /> : null}
                      {session.appointments_booked ? <Chip size="small" color="success" label="Booking" /> : null}
                      {!session.escalated && !session.appointments_booked ? <Typography variant="body2">{session.topic || "Enquiry"}</Typography> : null}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      </Box>
    </PageContainer>
  );
}
