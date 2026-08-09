"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import type { OutreachReply } from "@/components/outreach/types";
import {
  fetchOutreachReplies,
  postOutreachInboundReply,
  resolveOutreachReply,
} from "@/lib/outreach-api";

const WORKSPACE = "default";

const CLASSIFICATIONS = [
  "interested",
  "booking_intent",
  "question",
  "objection",
  "not_interested",
  "not_now",
  "unsubscribe",
  "ooo",
  "unknown",
] as const;

function replyList(data: { replies?: OutreachReply[]; reviews?: OutreachReply[] } | undefined): OutreachReply[] {
  return data?.replies ?? data?.reviews ?? [];
}

export default function OutreachRepliesPage() {
  const [filter, setFilter] = React.useState<"open" | "resolved" | "all">("open");
  const [fromEmail, setFromEmail] = React.useState("lead@example.com");
  const [subject, setSubject] = React.useState("Re: discovery");
  const [body, setBody] = React.useState("Sounds good, can we book a call?");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const resolvedParam = filter === "all" ? undefined : filter === "resolved" ? 1 : 0;
  const replies = useSWR(["outreach-replies", WORKSPACE, filter], () =>
    fetchOutreachReplies(WORKSPACE, resolvedParam as 0 | 1 | undefined),
  );

  const onInbound = async () => {
    setBusy(true);
    setError(null);
    try {
      await postOutreachInboundReply(
        { from_email: fromEmail, subject, body },
        WORKSPACE,
      );
      setMessage("Inbound reply processed");
      await replies.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not ingest reply");
    } finally {
      setBusy(false);
    }
  };

  const onResolve = async (replyId: string, classification: string) => {
    setBusy(true);
    setError(null);
    try {
      await resolveOutreachReply(replyId, { classification }, WORKSPACE);
      setMessage("Reply reviewed");
      await replies.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not resolve reply");
    } finally {
      setBusy(false);
    }
  };

  const items = replyList(replies.data);

  return (
    <Stack spacing={2}>
      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={1} alignItems={{ sm: "center" }}>
        <Typography variant="body2" color="text.secondary">
          Unknown replies stay open for manual review. Interest and booking intent promote leads automatically.
        </Typography>
        <ButtonGroup size="small">
          {(["open", "resolved", "all"] as const).map((value) => (
            <Button key={value} variant={filter === value ? "contained" : "outlined"} onClick={() => setFilter(value)}>
              {value}
            </Button>
          ))}
        </ButtonGroup>
      </Stack>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Record inbound reply
          </Typography>
          <Stack spacing={1.5}>
            <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
              <TextField size="small" fullWidth label="From" value={fromEmail} onChange={(e) => setFromEmail(e.target.value)} />
              <TextField size="small" fullWidth label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
            </Stack>
            <TextField
              fullWidth
              multiline
              minRows={3}
              label="Body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
            <Button size="small" variant="contained" disabled={busy} onClick={() => void onInbound()} sx={{ alignSelf: "flex-start" }}>
              Process reply
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {replies.isLoading && !replies.data ? (
        <Typography color="text.secondary">Loading replies...</Typography>
      ) : items.length === 0 ? (
        <Typography color="text.secondary">No replies in this view.</Typography>
      ) : (
        <Stack spacing={1}>
          {items.map((review) => {
            const leadId = review.lead_id || review.leadId;
            const from = review.from_email || review.fromEmail || "Unknown";
            const preview = review.body_preview || review.bodyPreview || review.body || "";
            const open = review.status === "open" || review.resolved === false || (!review.status && !review.resolved);
            return (
              <Card key={review.id} variant="outlined">
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" spacing={1} flexWrap="wrap" useFlexGap>
                    <Typography variant="body2" fontWeight={600}>
                      {from} · {review.classification || "unknown"}
                      {typeof review.confidence === "number"
                        ? ` (${Math.round(review.confidence * 100)}%)`
                        : ""}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {review.status || (review.resolved ? "resolved" : "open")}
                    </Typography>
                  </Stack>
                  <Typography variant="caption" color="text.secondary" display="block">
                    {review.subject}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    {preview}
                  </Typography>
                  {(review.suggested_reply || review.suggestedReply) && (
                    <Typography
                      component="pre"
                      variant="caption"
                      color="text.secondary"
                      sx={{ mt: 1, p: 1, bgcolor: "action.hover", borderRadius: 1, whiteSpace: "pre-wrap" }}
                    >
                      {review.suggested_reply || review.suggestedReply}
                    </Typography>
                  )}
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }}>
                    {leadId ? (
                      <Button size="small" variant="outlined" component="a" href={`/outreach/leads/${leadId}`}>
                        Open lead
                      </Button>
                    ) : null}
                    {open
                      ? CLASSIFICATIONS.map((classification) => (
                          <Button
                            key={classification}
                            size="small"
                            disabled={busy}
                            onClick={() => void onResolve(review.id, classification)}
                          >
                            {classification.replace(/_/g, " ")}
                          </Button>
                        ))
                      : null}
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Stack>
      )}
    </Stack>
  );
}
