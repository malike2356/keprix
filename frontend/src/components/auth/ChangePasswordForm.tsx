"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { changeAccountPassword } from "@/lib/account-api";

export default function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = React.useState("");
  const [newPassword, setNewPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setMessage(null);

    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await changeAccountPassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage("Password updated. Other signed-in devices were signed out.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Password change failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
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
        Use at least 8 characters. Changing your password signs out other active sessions.
      </Typography>
      <TextField
        label="Current password"
        type="password"
        value={currentPassword}
        onChange={(event) => setCurrentPassword(event.target.value)}
        required
        autoComplete="current-password"
        fullWidth
      />
      <TextField
        label="New password"
        type="password"
        value={newPassword}
        onChange={(event) => setNewPassword(event.target.value)}
        required
        autoComplete="new-password"
        fullWidth
        helperText="Minimum 8 characters"
      />
      <TextField
        label="Confirm new password"
        type="password"
        value={confirmPassword}
        onChange={(event) => setConfirmPassword(event.target.value)}
        required
        autoComplete="new-password"
        fullWidth
      />
      <Box>
        <Button type="submit" variant="contained" disabled={submitting}>
          {submitting ? "Updating..." : "Update password"}
        </Button>
      </Box>
    </Box>
  );
}
