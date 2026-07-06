"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import TextField from "@mui/material/TextField";
import NextLink from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";
import { useCESession } from "@/lib/ce-auth";

export default function LoginForm({ returnTo = "/launcher" }: { returnTo?: string }) {
  const router = useRouter();
  const { signIn } = useCESession();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [remember, setRemember] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await signIn(email, password);
      router.push(returnTo.startsWith("/") ? returnTo : "/launcher");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {error ? <Alert severity="error">{error}</Alert> : null}
      <TextField
        label="Email or username"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        autoComplete="username"
        fullWidth
      />
      <TextField
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
        autoComplete="current-password"
        fullWidth
      />
      <FormControlLabel
        control={<Checkbox checked={remember} onChange={(e) => setRemember(e.target.checked)} />}
        label="Remember me"
      />
      <Button type="submit" variant="contained" size="large" disabled={submitting}>
        {submitting ? "Signing in..." : "Sign in"}
      </Button>
      <Button component={NextLink} href="/auth/setup" variant="text">
        First time? Set up your instance
      </Button>
    </Box>
  );
}
