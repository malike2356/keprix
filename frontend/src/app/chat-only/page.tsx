"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import MicNoneIcon from "@mui/icons-material/MicNone";
import SendIcon from "@mui/icons-material/Send";
import * as React from "react";
import { ceApi } from "@/lib/ce-api";
import { createConversation } from "@/lib/workspace-api";

type Message = { role: "user" | "assistant"; content: string };

export default function ChatOnlyPage() {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [text, setText] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [notice, setNotice] = React.useState<string | null>(null);
  const session = React.useRef<string | null>(null);

  React.useEffect(() => {
    if ("serviceWorker" in navigator) void navigator.serviceWorker.register("/sw.js", { scope: "/chat-only" });
  }, []);

  async function send() {
    const content = text.trim();
    if (!content || busy) return;
    setBusy(true);
    setNotice(null);
    setMessages((current) => [...current, { role: "user", content }]);
    setText("");
    try {
      if (!session.current) session.current = (await createConversation(content.slice(0, 80))).id;
      const response = await ceApi(`/api/conversations/${session.current}/messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      if (!response.ok || !response.body) throw new Error("Chat is unavailable. Check your connection and retry.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let answer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        for (const line of buffer.split("\n").slice(0, -1)) {
          if (!line.trim()) continue;
          const event = JSON.parse(line) as { event?: string; delta?: string; message?: { content?: unknown } };
          if (event.delta) answer += event.delta;
          if (event.event === "message_done" && typeof event.message?.content === "string") answer = event.message.content;
        }
        buffer = buffer.slice(buffer.lastIndexOf("\n") + 1);
      }
      setMessages((current) => [...current, { role: "assistant", content: answer || "The agent returned no text." }]);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Chat failed. Retry when online.");
    } finally {
      setBusy(false);
    }
  }

  function listen() {
    const Recognition = (window as Window & { SpeechRecognition?: new () => { lang: string; start: () => void; onresult: (event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void; onerror: () => void } }).SpeechRecognition;
    if (!Recognition) {
      setNotice("Voice input is not available in this browser.");
      return;
    }
    const recognition = new Recognition();
    recognition.lang = "en-GB";
    recognition.onresult = (event) => setText(Array.from(event.results).map((result) => result[0].transcript).join(" "));
    recognition.onerror = () => setNotice("Voice input failed. You can type the message instead.");
    recognition.start();
  }

  return (
    <Box sx={{ minHeight: "100dvh", bgcolor: "background.default", display: "flex", justifyContent: "center", p: { xs: 1, sm: 3 } }}>
      <Stack sx={{ width: "100%", maxWidth: 760, minHeight: "calc(100dvh - 16px)" }} spacing={1.5}>
        <Typography variant="h6" sx={{ px: 1, pt: 1 }}>Keprix Chat</Typography>
        <Paper variant="outlined" sx={{ flex: 1, p: { xs: 1.5, sm: 3 }, overflow: "auto" }}>
          {messages.length === 0 ? <Typography color="text.secondary">Ask your agent anything in this workspace.</Typography> : null}
          <Stack spacing={1.5}>
            {messages.map((message, index) => <Box key={index} sx={{ alignSelf: message.role === "user" ? "flex-end" : "flex-start", maxWidth: "92%", bgcolor: message.role === "user" ? "primary.main" : "action.hover", color: message.role === "user" ? "primary.contrastText" : "text.primary", borderRadius: 1, px: 1.5, py: 1 }}><Typography sx={{ whiteSpace: "pre-wrap" }}>{message.content}</Typography></Box>)}
          </Stack>
        </Paper>
        {notice ? <Alert severity="warning">{notice}</Alert> : null}
        <Stack direction="row" spacing={1} alignItems="center">
          <TextField fullWidth multiline maxRows={4} size="small" label="Message" value={text} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); } }} />
          <IconButton aria-label="Use voice input" onClick={listen}><MicNoneIcon /></IconButton>
          <Button aria-label="Send message" variant="contained" onClick={() => void send()} disabled={busy || !text.trim()}>{busy ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}</Button>
        </Stack>
      </Stack>
    </Box>
  );
}
