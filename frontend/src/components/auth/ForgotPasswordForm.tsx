"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { requestPasswordReset } from "@/lib/account-api";

export default function ForgotPasswordForm() {
  const [emailOrUsername, setEmailOrUsername] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setSubmitting(true);
    try {
      const responseMessage = await requestPasswordReset(emailOrUsername.trim());
      setMessage(responseMessage);
      setEmailOrUsername("");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Request failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Typography variant="body2" color="text.secondary">
        Enter your email or username. If an account exists, we will send reset instructions.
      </Typography>
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
      <TextField
        label="Email or username"
        value={emailOrUsername}
        onChange={(event) => setEmailOrUsername(event.target.value)}
        required
        autoComplete="username"
        fullWidth
      />
      <Button type="submit" variant="contained" size="large" disabled={submitting}>
        {submitting ? "Sending..." : "Send reset link"}
      </Button>
    </Box>
  );
}
