"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { dryRunPlaybook } from "@/lib/multiagent-api";

type RunStreamPanelProps = {
  playbookName: string;
};

export default function RunStreamPanel({ playbookName }: RunStreamPanelProps) {
  const [input, setInput] = React.useState("Coordinate a research summary with citations");
  const [events, setEvents] = React.useState<Array<{ event_type: string; payload: Record<string, unknown> }>>([]);
  const [messages, setMessages] = React.useState<Array<{ sender: string; recipient: string; content: string }>>([]);
  const [error, setError] = React.useState<string | null>(null);
  const [running, setRunning] = React.useState(false);

  async function handleDryRun() {
    setRunning(true);
    setError(null);
    try {
      const result = await dryRunPlaybook(playbookName, input);
      setEvents((result.events ?? []) as typeof events);
      setMessages((result.messages ?? []) as typeof messages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dry run failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" sx={{ mb: 2 }}>
          Run stream (dry-run)
        </Typography>
        <TextField
          fullWidth
          multiline
          minRows={2}
          size="small"
          label="Coordination input"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          sx={{ mb: 2 }}
        />
        <Button size="small" variant="contained" onClick={handleDryRun} disabled={running || !playbookName}>
          Run dry-run
        </Button>
        {error ? (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        ) : null}
        <Box sx={{ mt: 2 }}>
          {events.map((event, index) => (
            <Box key={`event-${index}`} sx={{ mb: 1.5 }}>
              <Typography variant="caption" color="text.secondary">
                {event.event_type}
              </Typography>
              <StructuredDataView
                value={
                  (event.payload as { message?: string }).message
                    ? { message: (event.payload as { message?: string }).message, ...event.payload }
                    : event.payload
                }
              />
            </Box>
          ))}
          {messages.map((message, index) => (
            <Typography key={`msg-${index}`} variant="body2" sx={{ mb: 0.5 }}>
              {message.sender} {"->"} {message.recipient}: {message.content}
            </Typography>
          ))}
        </Box>
      </CardContent>
    </Card>
  );
}
