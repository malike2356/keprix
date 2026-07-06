"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import {
  fetchNotifyExternalConfig,
  listNotifyExternalDeliveries,
  saveNotifyExternalConfig,
  sendNotifyExternalTestEmail,
} from "@/lib/notify-external-api";

export default function ExternalNotificationsPage() {
  const { data: config, mutate } = useSWR("notify-external-config", fetchNotifyExternalConfig);
  const { data: deliveries } = useSWR("notify-external-deliveries", listNotifyExternalDeliveries);
  const [smtpHost, setSmtpHost] = React.useState("");
  const [smtpPort, setSmtpPort] = React.useState("587");
  const [smtpUser, setSmtpUser] = React.useState("");
  const [smtpPassword, setSmtpPassword] = React.useState("");
  const [fromEmail, setFromEmail] = React.useState("");
  const [fromName, setFromName] = React.useState("Keprix");
  const [testEmail, setTestEmail] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!config) return;
    setSmtpHost(config.smtp_host ?? "");
    setSmtpPort(String(config.smtp_port ?? 587));
    setSmtpUser(config.smtp_username ?? "");
    setFromEmail(config.smtp_from_email ?? "");
    setFromName(config.smtp_from_name ?? "Keprix");
  }, [config]);

  const onSave = async () => {
    setError(null);
    setMessage(null);
    try {
      await saveNotifyExternalConfig({
        smtp_host: smtpHost,
        smtp_port: Number(smtpPort),
        smtp_use_tls: true,
        smtp_username: smtpUser,
        smtp_password: smtpPassword || undefined,
        smtp_from_email: fromEmail,
        smtp_from_name: fromName,
      });
      setSmtpPassword("");
      await mutate();
      setMessage("SMTP configuration saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  };

  const onTest = async () => {
    setError(null);
    setMessage(null);
    try {
      const result = await sendNotifyExternalTestEmail(testEmail);
      setMessage(`Test email queued: ${result.notification_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test email failed");
    }
  };

  return (
    <Box>
      <PageHeader
        title="External notifications"
        description="SMTP and webhook delivery to external reviewers, auditors, and compliance contacts."
      />
      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      <Stack spacing={2} sx={{ maxWidth: 560 }}>
        <TextField label="SMTP host" value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} />
        <TextField label="SMTP port" value={smtpPort} onChange={(e) => setSmtpPort(e.target.value)} />
        <TextField label="SMTP username" value={smtpUser} onChange={(e) => setSmtpUser(e.target.value)} />
        <TextField
          label="SMTP password"
          type="password"
          value={smtpPassword}
          onChange={(e) => setSmtpPassword(e.target.value)}
          helperText={config?.smtp_password_vault_id === "configured" ? "Password already stored" : ""}
        />
        <TextField label="From email" value={fromEmail} onChange={(e) => setFromEmail(e.target.value)} />
        <TextField label="From name" value={fromName} onChange={(e) => setFromName(e.target.value)} />
        <Button variant="contained" onClick={onSave}>Save SMTP settings</Button>
        <TextField label="Test recipient" value={testEmail} onChange={(e) => setTestEmail(e.target.value)} />
        <Button variant="outlined" onClick={onTest} disabled={!testEmail}>Send test email</Button>
      </Stack>
      <Typography variant="h6" sx={{ mt: 4, mb: 1 }}>Recent deliveries</Typography>
      <Stack spacing={1}>
        {(deliveries?.notifications ?? []).map((row: { id: string; channel: string; recipient_domain: string; status: string; subject?: string }) => (
          <Box key={row.id} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1, p: 1.5 }}>
            <Typography variant="body2">{row.channel} to {row.recipient_domain}</Typography>
            <Typography variant="caption" color="text.secondary">{row.status} {row.subject ? `- ${row.subject}` : ""}</Typography>
          </Box>
        ))}
      </Stack>
    </Box>
  );
}
