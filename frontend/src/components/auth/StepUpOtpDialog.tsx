"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { sendEmailOtp, verifyEmailOtpStepUp } from "@/lib/account-api";
import { setStepUpToken } from "@/lib/step-up-token";

type StepUpOtpDialogProps = {
  open: boolean;
  title?: string;
  description?: string;
  onClose: () => void;
  onVerified: (stepUpToken: string) => void;
};

export default function StepUpOtpDialog({
  open,
  title = "Verify by email",
  description = "We will send a 6-digit code to your account email.",
  onClose,
  onVerified,
}: StepUpOtpDialogProps) {
  const [challengeId, setChallengeId] = React.useState<string | null>(null);
  const [code, setCode] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      setChallengeId(null);
      setCode("");
      setError(null);
      setMessage(null);
    }
  }, [open]);

  const handleSend = async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await sendEmailOtp(undefined, "step_up");
      setChallengeId(result.challengeId);
      setMessage(result.message);
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "Failed to send code");
    } finally {
      setBusy(false);
    }
  };

  const handleVerify = async () => {
    if (!challengeId) return;
    setBusy(true);
    setError(null);
    try {
      const stepUpToken = await verifyEmailOtpStepUp(challengeId, code.trim());
      setStepUpToken(stepUpToken);
      onVerified(stepUpToken);
      onClose();
    } catch (verifyError) {
      setError(verifyError instanceof Error ? verifyError.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
        <Typography variant="body2" color="text.secondary">
          {description}
        </Typography>
        {error ? <Alert severity="error">{error}</Alert> : null}
        {message ? <Alert severity="success">{message}</Alert> : null}
        {!challengeId ? (
          <Button variant="contained" onClick={() => void handleSend()} disabled={busy}>
            {busy ? "Sending..." : "Send email code"}
          </Button>
        ) : (
          <TextField
            label="6-digit email code"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            inputProps={{ inputMode: "numeric", pattern: "[0-9]*", maxLength: 6 }}
            fullWidth
          />
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        {challengeId ? (
          <Button variant="contained" onClick={() => void handleVerify()} disabled={busy || code.trim().length !== 6}>
            Verify
          </Button>
        ) : null}
      </DialogActions>
    </Dialog>
  );
}
