"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useParams } from "next/navigation";
import * as React from "react";
import { openPublicSession, publicStatus, sendPublicMessage } from "@/lib/concierge-api";

export default function ConciergeEmbedPage() {
  const params = useParams<{ workspaceId: string; personaId: string }>();
  const workspaceId = String(params.workspaceId || "");
  const personaId = String(params.personaId || "default");
  const [published, setPublished] = React.useState(false);
  const [greeting, setGreeting] = React.useState<string | null>(null);
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  const [messages, setMessages] = React.useState<Array<{ role: string; text: string }>>([]);
  const [input, setInput] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    void (async () => {
      try {
        const status = await publicStatus(workspaceId, personaId);
        setPublished(status.published);
        setGreeting(status.greeting);
        if (!status.published) {
          setError("This concierge is not published.");
          return;
        }
        const session = await openPublicSession(workspaceId, personaId);
        setSessionId(session.sessionId);
        if (session.greeting) {
          setMessages([{ role: "concierge", text: session.greeting }]);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to start chat");
      }
    })();
  }, [workspaceId, personaId]);

  const onSend = async () => {
    if (!sessionId || !input.trim()) return;
    const text = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "visitor", text }]);
    try {
      const res = await sendPublicMessage(workspaceId, personaId, sessionId, text);
      setMessages((m) => [...m, { role: "concierge", text: res.reply }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed");
    }
  };

  return (
    <Box sx={{ minHeight: "100vh", p: 2, bgcolor: "background.default", color: "text.primary" }}>
      <Stack spacing={1} maxWidth={420} mx="auto">
        <Typography variant="h6">Customer Concierge</Typography>
        {!published && error ? <Typography color="error">{error}</Typography> : null}
        <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 2, minHeight: 320, bgcolor: "background.paper" }}>
          {messages.map((m, i) => (
            <Typography key={`${m.role}-${i}`} variant="body2" sx={{ mb: 1 }}>
              <strong>{m.role === "visitor" ? "You" : "Concierge"}:</strong> {m.text}
            </Typography>
          ))}
          {!messages.length && greeting ? (
            <Typography variant="body2">{greeting}</Typography>
          ) : null}
        </Box>
        <Stack direction="row" spacing={1}>
          <TextField
            size="small"
            fullWidth
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={!sessionId}
            placeholder="Ask a question"
          />
          <Button variant="contained" onClick={() => void onSend()} disabled={!sessionId}>
            Send
          </Button>
        </Stack>
        <Typography variant="caption" color="text.secondary">
          Visitor session (not a workspace member).
        </Typography>
      </Stack>
    </Box>
  );
}
