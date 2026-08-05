"use client";

import Close from "@mui/icons-material/Close";
import SmartToyOutlined from "@mui/icons-material/SmartToyOutlined";
import Alert from "@mui/material/Alert";
import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Drawer from "@mui/material/Drawer";
import Fab from "@mui/material/Fab";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { usePathname } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import {
  fetchOperatorContext,
  streamOperatorCopilotMessage,
  type OperatorContextBundle,
  type OperatorCopilotEvent,
} from "@/lib/operator-api";
import { labelForPath } from "@/lib/navigation";

type DrawerProps = {
  open: boolean;
  onClose: () => void;
};

type PanelProps = {
  embedded?: boolean;
};

type ChatTurn = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  approval?: {
    action: string;
    actionId?: string;
    recordId?: string;
    runId?: string;
    summary?: string;
  };
};

const SUGGESTIONS = [
  "What page am I on?",
  "What needs my approval?",
  "Why did my last playbook fail?",
  "Which channel is unhealthy?",
] as const;

function attentionCount(context?: OperatorContextBundle | null): number {
  if (!context) return 0;
  return (context.staged_mutations || 0) + (context.interrupted_playbooks || 0) + (context.channel_issues?.length || 0);
}

function formatSummaryPlain(markdown: string): string {
  return markdown
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .trim();
}

export function useOperatorAttentionBadge(): number {
  const { data } = useSWR("operator-context-nav", () => fetchOperatorContext("default", "nav"), {
    revalidateOnFocus: true,
    refreshInterval: 60_000,
    shouldRetryOnError: false,
  });
  return attentionCount(data);
}

export function OperatorCopilotFab({
  onClick,
  badge,
}: {
  onClick: () => void;
  badge?: number;
}) {
  return (
    <Fab
      color="primary"
      aria-label="Open operator copilot"
      onClick={onClick}
      sx={{ position: "fixed", right: 24, bottom: 24 }}
    >
      <Badge color="warning" badgeContent={badge || 0}>
        <SmartToyOutlined />
      </Badge>
    </Fab>
  );
}

function OperatorCopilotBody({ embedded = false }: PanelProps) {
  const pathname = usePathname() || "/";
  const pageLabel = labelForPath(pathname);
  const { data, error, isLoading, mutate } = useSWR(
    "operator-context-full",
    () => fetchOperatorContext("default", "full"),
    { revalidateOnFocus: true, shouldRetryOnError: false },
  );
  const [input, setInput] = React.useState("");
  const [turns, setTurns] = React.useState<ChatTurn[]>([]);
  const [streaming, setStreaming] = React.useState(false);
  const [sendError, setSendError] = React.useState<string | null>(null);
  const abortRef = React.useRef<AbortController | null>(null);

  React.useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const send = async (text: string, confirmAction?: Record<string, unknown> | null) => {
    const trimmed = text.trim();
    if (!trimmed || streaming) return;
    setSendError(null);
    const userTurn: ChatTurn = {
      id: `u-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    const assistantId = `a-${Date.now()}`;
    setTurns((prev) => [...prev, userTurn, { id: assistantId, role: "assistant", content: "" }]);
    setInput("");
    setStreaming(true);
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    let approval: ChatTurn["approval"];
    try {
      await streamOperatorCopilotMessage(trimmed, {
        signal: controller.signal,
        confirmAction: confirmAction ?? null,
        pagePath: pathname,
        pageLabel,
        onEvent: (event: OperatorCopilotEvent) => {
          if (event.event === "text_delta" && typeof event.content === "string") {
            setTurns((prev) =>
              prev.map((turn) =>
                turn.id === assistantId ? { ...turn, content: `${turn.content}${event.content}` } : turn,
              ),
            );
          }
          if (event.event === "approval") {
            approval = {
              action: String(event.action || ""),
              actionId: event.action_id,
              recordId: event.record_id,
              runId: event.run_id,
              summary: event.summary,
            };
            setTurns((prev) =>
              prev.map((turn) => (turn.id === assistantId ? { ...turn, approval } : turn)),
            );
          }
        },
      });
      await mutate();
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      const message = err instanceof Error ? err.message : "Operator copilot failed";
      setSendError(message);
      setTurns((prev) =>
        prev.map((turn) =>
          turn.id === assistantId
            ? { ...turn, content: turn.content || `Error: ${message}` }
            : turn,
        ),
      );
    } finally {
      setStreaming(false);
    }
  };

  const confirmPending = async (turn: ChatTurn) => {
    if (!turn.approval) return;
    const payload: Record<string, unknown> = {
      action: turn.approval.action,
      action_id: turn.approval.actionId,
    };
    if (turn.approval.recordId) payload.record_id = turn.approval.recordId;
    if (turn.approval.runId) payload.run_id = turn.approval.runId;
    await send(`Confirm ${turn.approval.action}`, payload);
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        height: embedded ? 420 : "100%",
        minHeight: embedded ? 420 : 0,
      }}
    >
      {isLoading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
          <CircularProgress size={28} />
        </Box>
      ) : error ? (
        <Alert
          severity="warning"
          action={
            <Button color="inherit" size="small" onClick={() => void mutate()}>
              Retry
            </Button>
          }
        >
          Operator context is unavailable. {error instanceof Error ? error.message : "Backend may still be starting."}
        </Alert>
      ) : data ? (
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
          <Chip size="small" variant="outlined" label={`Page: ${pageLabel}`} />
          <Chip size="small" color={data.staged_mutations ? "warning" : "default"} label={`Staged ${data.staged_mutations}`} />
          <Chip
            size="small"
            color={data.interrupted_playbooks ? "warning" : "default"}
            label={`Interrupted ${data.interrupted_playbooks}`}
          />
          <Chip
            size="small"
            color={data.channel_issues?.length ? "error" : "success"}
            label={`Channels ${data.channel_issues?.length ? `${data.channel_issues.length} issue(s)` : "ok"}`}
          />
        </Stack>
      ) : null}

      {data?.summary_markdown ? (
        <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: "pre-wrap" }}>
          {formatSummaryPlain(data.summary_markdown)}
        </Typography>
      ) : null}

      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
        {SUGGESTIONS.map((prompt) => (
          <Chip
            key={prompt}
            size="small"
            label={prompt}
            onClick={() => void send(prompt)}
            disabled={streaming || Boolean(error)}
          />
        ))}
      </Stack>

      <Box
        sx={{
          flex: 1,
          overflowY: "auto",
          border: 1,
          borderColor: "divider",
          borderRadius: 1,
          p: 1.5,
          bgcolor: "background.default",
          minHeight: 160,
        }}
      >
        {turns.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            Ask about this page, approvals, failed playbooks, or channel health.
          </Typography>
        ) : (
          <Stack spacing={1.5}>
            {turns.map((turn) => (
              <Box key={turn.id}>
                <Typography variant="caption" color="text.secondary">
                  {turn.role === "user" ? "You" : "Operator copilot"}
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                  {turn.content || (streaming ? "…" : "")}
                </Typography>
                {turn.approval ? (
                  <Button
                    size="small"
                    variant="contained"
                    sx={{ mt: 1 }}
                    disabled={streaming}
                    onClick={() => void confirmPending(turn)}
                  >
                    Confirm {turn.approval.action.replace(/_/g, " ")}
                  </Button>
                ) : null}
              </Box>
            ))}
          </Stack>
        )}
      </Box>

      {sendError ? (
        <Alert severity="error" onClose={() => setSendError(null)}>
          {sendError}
        </Alert>
      ) : null}

      <Box sx={{ display: "flex", gap: 1 }}>
        <TextField
          size="small"
          fullWidth
          placeholder="Ask the operator copilot…"
          value={input}
          disabled={streaming || Boolean(error)}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void send(input);
            }
          }}
        />
        <Button variant="contained" disabled={streaming || !input.trim() || Boolean(error)} onClick={() => void send(input)}>
          {streaming ? <CircularProgress size={18} color="inherit" /> : "Send"}
        </Button>
      </Box>
    </Box>
  );
}

export function OperatorCopilotPanel({ embedded = false }: PanelProps) {
  return (
    <Box>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Operator copilot
      </Typography>
      <OperatorCopilotBody embedded={embedded} />
    </Box>
  );
}

export default function OperatorCopilotDrawer({ open, onClose }: DrawerProps) {
  return (
    <Drawer anchor="right" open={open} onClose={onClose}>
      <Box sx={{ width: { xs: 320, sm: 420 }, p: 2, height: "100%", display: "flex", flexDirection: "column" }}>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
          <Typography variant="h6">Operator copilot</Typography>
          <IconButton aria-label="Close operator copilot" onClick={onClose}>
            <Close />
          </IconButton>
        </Box>
        <Box sx={{ flex: 1, minHeight: 0 }}>
          {open ? <OperatorCopilotBody /> : null}
        </Box>
      </Box>
    </Drawer>
  );
}
