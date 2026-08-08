"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import {
  approveOutreachApproval,
  fetchOutreachApprovals,
  rejectOutreachApproval,
} from "@/lib/outreach-api";

const WORKSPACE = "default";

export default function OutreachApprovalsPage() {
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busyId, setBusyId] = React.useState<string | null>(null);

  const approvals = useSWR(["outreach-approvals", WORKSPACE], () => fetchOutreachApprovals(WORKSPACE));

  const act = async (id: string, action: "approve" | "reject") => {
    setBusyId(id);
    setError(null);
    try {
      if (action === "approve") await approveOutreachApproval(id, WORKSPACE);
      else await rejectOutreachApproval(id, WORKSPACE);
      setMessage(action === "approve" ? "Send approved" : "Send rejected");
      await approvals.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not ${action} send`);
    } finally {
      setBusyId(null);
    }
  };

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

      <Typography variant="body2" color="text.secondary">
        Pending Soft Wall messages wait here before outbound send. No mass-send without approval.
      </Typography>

      {approvals.isLoading && !approvals.data ? (
        <Typography color="text.secondary">Loading approvals...</Typography>
      ) : (approvals.data?.approvals ?? []).length === 0 ? (
        <Typography color="text.secondary">No pending Soft Wall approvals.</Typography>
      ) : (
        <Stack spacing={1.5}>
          {(approvals.data?.approvals ?? []).map((item) => {
            const recipient = item.recipient || item.to || "Unknown recipient";
            const body = item.draft_body || item.draftBody || item.body || "";
            return (
              <Card key={item.id} variant="outlined">
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" spacing={1} flexWrap="wrap" useFlexGap>
                    <Typography variant="body2" fontWeight={600}>
                      {recipient}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.status || "pending"}
                      {item.category ? ` · ${item.category}` : ""}
                    </Typography>
                  </Stack>
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    {item.subject || "(no subject)"}
                  </Typography>
                  {body ? (
                    <Typography
                      component="pre"
                      variant="caption"
                      color="text.secondary"
                      sx={{
                        mt: 1.5,
                        p: 1.5,
                        bgcolor: "action.hover",
                        borderRadius: 1,
                        whiteSpace: "pre-wrap",
                        maxHeight: 220,
                        overflow: "auto",
                      }}
                    >
                      {body}
                    </Typography>
                  ) : null}
                  <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
                    <Button
                      size="small"
                      variant="contained"
                      disabled={busyId === item.id}
                      onClick={() => void act(item.id, "approve")}
                    >
                      Approve
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={busyId === item.id}
                      onClick={() => void act(item.id, "reject")}
                    >
                      Reject
                    </Button>
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
