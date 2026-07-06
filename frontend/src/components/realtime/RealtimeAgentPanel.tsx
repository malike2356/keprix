"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import * as React from "react";
import type { RealtimeEvent } from "@/lib/agents-runtime-api";
import { createRealtimeSession, fetchRealtimeTranscript, postRealtimeEvent } from "@/lib/agents-runtime-api";

type Props = {
  agent?: string;
};

export default function RealtimeAgentPanel({ agent = "echo_agent" }: Props) {
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  const [events, setEvents] = React.useState<RealtimeEvent[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const refreshTranscript = React.useCallback(async (id: string) => {
    const payload = await fetchRealtimeTranscript(id);
    setEvents(payload.transcript);
  }, []);

  const ensureSession = React.useCallback(async () => {
    if (sessionId) return sessionId;
    const session = await createRealtimeSession(agent);
    setSessionId(session.session_id);
    setEvents(session.events ?? []);
    return session.session_id as string;
  }, [agent, sessionId]);

  const pushEvent = async (type: string, text: string) => {
    setBusy(true);
    setError(null);
    try {
      const id = await ensureSession();
      await postRealtimeEvent(id, { type, text });
      await refreshTranscript(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Realtime request failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <Typography variant="subtitle2" gutterBottom>
        Realtime lane ({agent})
      </Typography>
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <Button size="small" disabled={busy} onClick={() => pushEvent("speech_in", "Caller greeting")}>
          Speech in
        </Button>
        <Button size="small" disabled={busy} onClick={() => pushEvent("speech_out", "Agent reply")}>
          Speech out
        </Button>
        <Button size="small" disabled={busy} onClick={() => pushEvent("interrupt", "")}>
          Interrupt
        </Button>
        <Button size="small" disabled={busy} onClick={() => pushEvent("tool_pause", "Awaiting tool approval")}>
          Tool pause
        </Button>
        <Button size="small" disabled={busy} onClick={() => pushEvent("escalation", "Summary sent to chat")}>
          Escalate
        </Button>
      </Box>
      {error ? (
        <Typography variant="body2" color="error" sx={{ mb: 1 }}>
          {error}
        </Typography>
      ) : null}
      <List dense>
        {events.map((event, index) => (
          <ListItem key={`${event.at}-${index}`} sx={{ px: 0 }}>
            <ListItemText
              primary={
                <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                  <Chip size="small" label={event.type} />
                  <Typography variant="body2">{event.text || "(no text)"}</Typography>
                </Box>
              }
              secondary={event.at}
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
}
