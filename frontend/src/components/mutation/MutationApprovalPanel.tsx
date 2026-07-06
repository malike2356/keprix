"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress"; // @loading-contract-ignore button submit spinners
import TextField from "@mui/material/TextField";
import * as React from "react";
import { approveMutation, rejectMutation } from "@/lib/mutation-api";

type MutationApprovalPanelProps = {
  mutationId: string;
  tier: string;
  promptKey?: string;
  onApproved?: () => void;
  onRejected?: () => void;
  compact?: boolean;
};

export default function MutationApprovalPanel({
  mutationId,
  tier,
  promptKey,
  onApproved,
  onRejected,
  compact = false,
}: MutationApprovalPanelProps) {
  const [loading, setLoading] = React.useState<"approve" | "reject" | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [reason, setReason] = React.useState("");

  const handleApprove = async () => {
    setLoading("approve");
    setError(null);
    try {
      await approveMutation(mutationId, tier, promptKey);
      onApproved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setLoading(null);
    }
  };

  const handleReject = async () => {
    setLoading("reject");
    setError(null);
    try {
      await rejectMutation(mutationId, tier, reason || "Rejected by operator");
      onRejected?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setLoading(null);
    }
  };

  return (
    <Box sx={{ display: "grid", gap: 1 }}>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {!compact ? (
        <TextField
          size="small"
          label="Reject reason"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          placeholder="Optional reason for rejection"
        />
      ) : null}
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        <Button
          size="small"
          variant="contained"
          color="success"
          disabled={loading !== null}
          onClick={() => void handleApprove()}
          startIcon={loading === "approve" ? <CircularProgress size={14} color="inherit" /> : undefined}
        >
          Approve
        </Button>
        <Button
          size="small"
          color="inherit"
          disabled={loading !== null}
          onClick={() => void handleReject()}
          startIcon={loading === "reject" ? <CircularProgress size={14} color="inherit" /> : undefined}
        >
          Reject
        </Button>
      </Box>
    </Box>
  );
}
