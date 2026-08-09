"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import {
  fetchNotificationPreferences,
  saveNotificationPreferences,
} from "@/lib/notifications-api";

const CHANNEL_LABELS: Record<string, string> = {
  in_app: "In-app inbox",
  email: "Email",
  push: "Mobile push",
  slack: "Slack",
  telegram: "Telegram",
  discord: "Discord",
  webchat: "WebChat",
};

export default function NotificationPreferencesPage() {
  const { data: prefs, mutate } = useSWR("notification-preferences", fetchNotificationPreferences);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);

  const [channels, setChannels] = React.useState<Record<string, boolean>>({});
  const [quietEnabled, setQuietEnabled] = React.useState(false);
  const [quietStart, setQuietStart] = React.useState("22:00");
  const [quietEnd, setQuietEnd] = React.useState("07:00");
  const [digestEnabled, setDigestEnabled] = React.useState(true);
  const [escalationDelay, setEscalationDelay] = React.useState(60);

  React.useEffect(() => {
    if (!prefs) return;
    setChannels(prefs.channels_enabled ?? {});
    setQuietEnabled(prefs.quiet_hours_enabled);
    setQuietStart(prefs.quiet_hours_start);
    setQuietEnd(prefs.quiet_hours_end);
    setDigestEnabled(prefs.digest_enabled);
    setEscalationDelay(prefs.escalation_delay_minutes);
  }, [prefs]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await saveNotificationPreferences({
        channels_enabled: channels,
        quiet_hours_enabled: quietEnabled,
        quiet_hours_start: quietStart,
        quiet_hours_end: quietEnd,
        digest_enabled: digestEnabled,
        escalation_delay_minutes: escalationDelay,
      });
      await mutate();
      setMessage("Notification preferences saved.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Notification preferences"
        description="Control channels, quiet hours, digests, and approval escalation timing."
        breadcrumbs={[
          { label: "Settings", href: "/settings" },
          { label: "Notifications" },
        ]}
        actions={
          <Button component="a" href="/notifications" size="small">
            Open inbox
          </Button>
        }
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Delivery channels
          </Typography>
          {Object.entries(CHANNEL_LABELS).map(([key, label]) => (
            <FormControlLabel
              key={key}
              control={
                <Switch
                  checked={Boolean(channels[key])}
                  onChange={(event) => setChannels((current) => ({ ...current, [key]: event.target.checked }))}
                />
              }
              label={label}
            />
          ))}
        </CardContent>
      </Card>

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Quiet hours
          </Typography>
          <FormControlLabel
            control={<Switch checked={quietEnabled} onChange={(event) => setQuietEnabled(event.target.checked)} />}
            label="Enable quiet hours (non-critical alerts queue for digest)"
          />
          <Box sx={{ display: "flex", gap: 2, mt: 2, flexWrap: "wrap" }}>
            <TextField label="Start" size="small" value={quietStart} onChange={(e) => setQuietStart(e.target.value)} />
            <TextField label="End" size="small" value={quietEnd} onChange={(e) => setQuietEnd(e.target.value)} />
          </Box>
          <FormControlLabel
            sx={{ mt: 2, display: "block" }}
            control={<Switch checked={digestEnabled} onChange={(event) => setDigestEnabled(event.target.checked)} />}
            label="Send digest email when quiet hours end"
          />
        </CardContent>
      </Card>

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Escalation
          </Typography>
          <TextField
            label="Approval reminder delay (minutes)"
            type="number"
            size="small"
            value={escalationDelay}
            onChange={(event) => setEscalationDelay(Number(event.target.value) || 60)}
            inputProps={{ min: 5, max: 1440 }}
          />
        </CardContent>
      </Card>

      <Button variant="contained" onClick={() => void handleSave()} disabled={saving}>
        Save preferences
      </Button>
    </Box>
  );
}
