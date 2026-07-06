"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import * as React from "react";
import NextLink from "next/link";
import useSWR from "swr";
import FeatureGateCard from "@/components/billing/FeatureGateCard";
import { getBackendBaseUrl } from "@/lib/ce-api";
import {
  deleteAgentAppSchedule,
  deleteAgentAppWebhook,
  fetchAgentAppSchedule,
  fetchAgentAppUsage,
  fetchAgentAppWebhook,
  rotateAgentAppWebhook,
  saveAgentAppSchedule,
  type AgentAppDetail,
} from "@/lib/agent-apps-api";

const CRON_PRESETS = [
  { label: "Daily 9am", cron: "0 9 * * *" },
  { label: "Weekdays 9am", cron: "0 9 * * 1-5" },
  { label: "Weekly Monday", cron: "0 9 * * 1" },
] as const;

type Props = {
  appName: string;
  app?: AgentAppDetail;
};

export default function AgentAppAutomate({ appName, app }: Props) {
  const [cron, setCron] = React.useState(app?.schedule?.suggested || "0 9 * * 1-5");
  const [timezone, setTimezone] = React.useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  );
  const [enabled, setEnabled] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [revealedWebhookUrl, setRevealedWebhookUrl] = React.useState<string | null>(null);
  const [showCurl, setShowCurl] = React.useState(false);

  const { data: scheduleData, mutate: mutateSchedule } = useSWR(
    ["agent-schedule", appName],
    () => fetchAgentAppSchedule(appName),
  );
  const { data: usageData } = useSWR("agent-apps-usage", fetchAgentAppUsage);
  const { data: webhookData, mutate: mutateWebhook } = useSWR(
    ["agent-webhook", appName],
    () => fetchAgentAppWebhook(appName),
  );

  React.useEffect(() => {
    const schedule = scheduleData?.schedule;
    if (!schedule) return;
    setCron(schedule.cron);
    setTimezone(schedule.timezone || timezone);
    setEnabled(schedule.enabled);
  }, [scheduleData?.schedule, timezone]);

  const webhook = webhookData?.webhook;
  const features = usageData?.usage?.features;
  const scheduleLocked = features?.scheduled === false;
  const webhookLocked = features?.webhooks === false;
  const apiBase = getBackendBaseUrl();
  const runCurl = `curl -X POST ${apiBase}/api/agent-apps/${appName}/run \\
  -H "Authorization: Bearer $KEPRIX_API_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"inputs":{}}'`;

  const webhookCurl =
    revealedWebhookUrl &&
    `curl -X POST "${revealedWebhookUrl}" \\
  -H "Content-Type: application/json" \\
  -d '{"inputs":{}}'`;

  const onSaveSchedule = async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await saveAgentAppSchedule(appName, { cron, timezone, enabled, inputs: {} });
      await mutateSchedule();
      setMessage(enabled ? "Schedule saved." : "Schedule paused.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save schedule");
    } finally {
      setBusy(false);
    }
  };

  const onClearSchedule = async () => {
    setBusy(true);
    setError(null);
    try {
      await deleteAgentAppSchedule(appName);
      setEnabled(false);
      await mutateSchedule();
      setMessage("Schedule removed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove schedule");
    } finally {
      setBusy(false);
    }
  };

  const onRotateWebhook = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await rotateAgentAppWebhook(appName);
      setRevealedWebhookUrl(result.webhook.url);
      await mutateWebhook();
      setMessage("Webhook URL rotated. Copy it now; it will be masked on refresh.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rotate webhook");
    } finally {
      setBusy(false);
    }
  };

  const onDisableWebhook = async () => {
    setBusy(true);
    setError(null);
    try {
      await deleteAgentAppWebhook(appName);
      setRevealedWebhookUrl(null);
      await mutateWebhook();
      setMessage("Webhook disabled.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disable webhook");
    } finally {
      setBusy(false);
    }
  };

  const copyText = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setMessage("Copied to clipboard.");
    } catch {
      setError("Copy failed");
    }
  };

  return (
    <Box sx={{ display: "grid", gap: 2, border: 1, borderColor: "divider", borderRadius: 2, p: 2 }}>
      <Typography variant="h6">Automate</Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}

      <Box>
        <Typography variant="subtitle2" gutterBottom>
          Schedule
        </Typography>
        {scheduleLocked ? (
          <FeatureGateCard
            title="Scheduled runs"
            description="Automate this app on a cron schedule."
            requiredPlan="Pro"
          />
        ) : (
          <>
        <FormControlLabel
          control={<Switch checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />}
          label="Run on schedule"
        />
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
          {CRON_PRESETS.map((preset) => (
            <Chip
              key={preset.cron}
              label={preset.label}
              size="small"
              onClick={() => setCron(preset.cron)}
              color={cron === preset.cron ? "primary" : "default"}
              variant={cron === preset.cron ? "filled" : "outlined"}
            />
          ))}
        </Stack>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 1 }}>
          <TextField
            size="small"
            label="Cron expression"
            value={cron}
            onChange={(e) => setCron(e.target.value)}
            fullWidth
          />
          <TextField
            size="small"
            label="Timezone"
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            fullWidth
          />
        </Stack>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Button variant="contained" size="small" onClick={() => void onSaveSchedule()} disabled={busy}>
            Save schedule
          </Button>
          {scheduleData?.schedule ? (
            <Button variant="outlined" size="small" onClick={() => void onClearSchedule()} disabled={busy}>
              Remove schedule
            </Button>
          ) : null}
          <Button component={NextLink} href="/admin/cron" size="small">
            Manage all schedules
          </Button>
        </Stack>
          </>
        )}
      </Box>

      <Box>
        <Typography variant="subtitle2" gutterBottom>
          Webhook
        </Typography>
        {webhookLocked ? (
          <FeatureGateCard
            title="Inbound webhooks"
            description="Trigger this app from external systems."
            requiredPlan="Team"
          />
        ) : (
          <>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Trigger this app from external systems without a UI session.
        </Typography>
        {webhook?.configured || revealedWebhookUrl ? (
          <Stack spacing={1}>
            <Stack direction="row" spacing={1} alignItems="center">
              <TextField
                size="small"
                fullWidth
                value={revealedWebhookUrl || webhook?.url || ""}
                InputProps={{ readOnly: true }}
              />
              <Button
                variant="outlined"
                size="small"
                startIcon={<ContentCopyIcon />}
                onClick={() => void copyText(revealedWebhookUrl || webhook?.url || "")}
                disabled={!revealedWebhookUrl && !webhook?.url}
              >
                Copy
              </Button>
            </Stack>
            {webhook?.token_last4 ? (
              <Typography variant="caption" color="text.secondary">
                Token ends with {webhook.token_last4}
              </Typography>
            ) : null}
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            No webhook configured yet.
          </Typography>
        )}
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Button variant="contained" size="small" onClick={() => void onRotateWebhook()} disabled={busy}>
            {webhook?.configured ? "Rotate URL" : "Create webhook URL"}
          </Button>
          {webhook?.configured ? (
            <Button variant="outlined" color="error" size="small" onClick={() => void onDisableWebhook()} disabled={busy}>
              Disable webhook
            </Button>
          ) : null}
          <Button
            size="small"
            endIcon={showCurl ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            onClick={() => setShowCurl((value) => !value)}
          >
            Example curl
          </Button>
        </Stack>
        <Collapse in={showCurl}>
          <Box sx={{ mt: 1, p: 1.5, bgcolor: "action.hover", borderRadius: 1 }}>
            <Typography variant="caption" component="pre" sx={{ whiteSpace: "pre-wrap", m: 0 }}>
              {webhookCurl || runCurl}
            </Typography>
          </Box>
        </Collapse>
          </>
        )}
      </Box>
    </Box>
  );
}
