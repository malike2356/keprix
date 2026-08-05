"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import AuthLayout from "@/components/auth/AuthLayout";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import { acceptWorkspaceInvite, fetchInvitePreview } from "@/lib/admin-workspace-api";
import { setCESession } from "@/lib/ce-api";

function AcceptInviteContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [preview, setPreview] = React.useState<{ email: string; role: string; message?: string } | null>(null);
  const [previewLoading, setPreviewLoading] = React.useState(Boolean(token));

  React.useEffect(() => {
    if (!token) {
      setError("Missing invite token");
      setPreviewLoading(false);
      return;
    }
    setPreviewLoading(true);
    fetchInvitePreview(token)
      .then((data) => {
        setPreview(data.invite);
        const local = data.invite.email.split("@")[0] || "";
        setUsername(local.replace(/[^a-z0-9._-]+/gi, "").toLowerCase());
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Invalid invite"))
      .finally(() => setPreviewLoading(false));
  }, [token]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await acceptWorkspaceInvite({
        token,
        password,
        username: username.trim() || undefined,
      });
      setCESession(result.token, {
        id: result.user.id,
        username: result.user.username,
        role: result.user.role,
        email: result.user.email || null,
      });
      router.replace("/home");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to accept invite");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <Typography variant="h5" gutterBottom>
        Accept workspace invite
      </Typography>
      {preview ? (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Join as <strong>{preview.email}</strong> with role <strong>{preview.role}</strong>.
        </Typography>
      ) : null}
      {preview?.message ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          {preview.message}
        </Alert>
      ) : null}
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      {previewLoading ? (
        <SkeletonDetailPanel fields={3} />
      ) : (
        <Box component="form" onSubmit={handleSubmit} sx={{ display: "grid", gap: 2 }}>
        <TextField
          label="Username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          required
          fullWidth
        />
        <TextField
          label="Password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
          fullWidth
        />
        <TextField
          label="Confirm password"
          type="password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          required
          fullWidth
        />
        <Button type="submit" variant="contained" size="large" disabled={loading || !token || !preview}>
          {loading ? "Creating account..." : "Accept invite"}
        </Button>
        </Box>
      )}
    </AuthLayout>
  );
}

export default function AcceptInvitePage() {
  return (
    <React.Suspense fallback={<Box sx={{ p: 4 }}><SkeletonDetailPanel fields={3} /></Box>}>
      <AcceptInviteContent />
    </React.Suspense>
  );
}
