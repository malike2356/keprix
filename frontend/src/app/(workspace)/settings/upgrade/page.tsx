"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import UpgradeWizardDialog from "@/components/upgrade/UpgradeWizardDialog";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import {
  checkUpgradeNow,
  dismissUpgradeAlert,
  fetchUpgradeChangelog,
  fetchUpgradeHistory,
  fetchUpgradeStatus,
  rollbackUpgrade,
  saveUpgradePreferences,
  severityColor,
  snoozeUpgradeAlert,
  type UpgradeAlert,
  type UpgradeAlertPreferences,
} from "@/lib/upgrade-api";

const SEVERITY_OPTIONS = ["critical", "high", "medium", "low", "info"] as const;
const DAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const DEFAULT_PREFS: UpgradeAlertPreferences = {
  in_app_enabled: true,
  in_app_min_severity: "medium",
  email_enabled: false,
  email_min_severity: "low",
  slack_enabled: false,
  slack_webhook_url: "",
  discord_enabled: false,
  discord_webhook_url: "",
  webhook_enabled: false,
  webhook_url: "",
  quiet_hours_enabled: false,
  quiet_hours_start: 22,
  quiet_hours_end: 7,
  auto_upgrade_policy: "manual",
  maintenance_day: 6,
  maintenance_hour: 3,
  require_tests_pass: true,
  notify_after_upgrade: true,
};

function SeveritySelect({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <FormControl size="small" sx={{ minWidth: 140 }} disabled={disabled}>
      <InputLabel>{label}</InputLabel>
      <Select
        label={label}
        value={value}
        onChange={(event) => onChange(String(event.target.value))}
      >
        {SEVERITY_OPTIONS.map((option) => (
          <MenuItem key={option} value={option}>
            {option}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}

function AlertCard({
  alert,
  busy,
  onUpgrade,
  onDismiss,
  onSnooze,
}: {
  alert: UpgradeAlert;
  busy: boolean;
  onUpgrade: () => void;
  onDismiss: () => void;
  onSnooze: () => void;
}) {
  return (
    <Card variant="outlined" sx={{ borderColor: `${severityColor(alert.severity)}.main` }}>
      <CardContent sx={{ display: "grid", gap: 1.5 }}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <Typography variant="subtitle1">{alert.title}</Typography>
          <Chip size="small" label={alert.severity.toUpperCase()} color={severityColor(alert.severity)} />
          <Chip size="small" label={`Risk ${alert.risk_level.toUpperCase()}`} variant="outlined" />
          <Chip size="small" label={`Target ${alert.target_version}`} variant="outlined" />
        </Stack>
        <Typography variant="body2" color="text.secondary">
          {alert.summary}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Features: {alert.feature_count} | Breaking: {alert.breaking_count}
          {alert.release_url ? (
            <>
              {" "}
              |{" "}
              <a href={alert.release_url} target="_blank" rel="noreferrer">
                Release notes
              </a>
            </>
          ) : null}
        </Typography>
        {!alert.compatible ? (
          <Alert severity="warning">Marked incompatible. Review carefully before applying.</Alert>
        ) : null}
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Button size="small" variant="contained" onClick={onUpgrade} disabled={busy}>
            Upgrade now
          </Button>
          <Button size="small" variant="outlined" onClick={onSnooze} disabled={busy}>
            Later (24h)
          </Button>
          <Button size="small" onClick={onDismiss} disabled={busy}>
            Dismiss
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default function SettingsUpgradePage() {
  const { data, error, isLoading, mutate } = useSWR("keprix-upgrade-status", fetchUpgradeStatus, {
    revalidateOnFocus: true,
    shouldRetryOnError: false,
  });
  const { data: history } = useSWR("keprix-upgrade-history", fetchUpgradeHistory, {
    shouldRetryOnError: false,
  });
  const { data: changelog } = useSWR("keprix-upgrade-changelog", () => fetchUpgradeChangelog(), {
    shouldRetryOnError: false,
  });

  const [prefs, setPrefs] = React.useState<UpgradeAlertPreferences>(DEFAULT_PREFS);
  const [prefsDirty, setPrefsDirty] = React.useState(false);
  const [savingPrefs, setSavingPrefs] = React.useState(false);
  const [checking, setChecking] = React.useState(false);
  const [busyAlertId, setBusyAlertId] = React.useState<string | null>(null);
  const [rollingBack, setRollingBack] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = React.useState(false);
  const [wizardTarget, setWizardTarget] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!data?.preferences || prefsDirty) return;
    setPrefs({ ...DEFAULT_PREFS, ...data.preferences });
  }, [data?.preferences, prefsDirty]);

  const updatePref = <K extends keyof UpgradeAlertPreferences>(key: K, value: UpgradeAlertPreferences[K]) => {
    setPrefs((current) => ({ ...current, [key]: value }));
    setPrefsDirty(true);
  };

  const runCheck = async () => {
    setChecking(true);
    setActionError(null);
    setMessage(null);
    try {
      const result = await checkUpgradeNow();
      await mutate();
      setMessage(
        result.update_available
          ? `Update available: ${result.target_version}`
          : "No newer installable release found.",
      );
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Upgrade check failed");
    } finally {
      setChecking(false);
    }
  };

  const savePrefs = async () => {
    setSavingPrefs(true);
    setActionError(null);
    setMessage(null);
    try {
      const saved = await saveUpgradePreferences(prefs);
      setPrefs(saved);
      setPrefsDirty(false);
      await mutate();
      setMessage("Upgrade notification preferences saved.");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to save preferences");
    } finally {
      setSavingPrefs(false);
    }
  };

  const openWizard = (target: string) => {
    setWizardTarget(target);
    setWizardOpen(true);
  };

  const onDismiss = async (alert: UpgradeAlert) => {
    setBusyAlertId(alert.id);
    setActionError(null);
    try {
      await dismissUpgradeAlert(alert.id);
      await mutate();
      setMessage(`Dismissed alert for ${alert.target_version}.`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Dismiss failed");
    } finally {
      setBusyAlertId(null);
    }
  };

  const onSnooze = async (alert: UpgradeAlert) => {
    setBusyAlertId(alert.id);
    setActionError(null);
    try {
      await snoozeUpgradeAlert(alert.id, 24);
      await mutate();
      setMessage(`Snoozed ${alert.target_version} for 24 hours.`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Snooze failed");
    } finally {
      setBusyAlertId(null);
    }
  };

  const onRollback = async () => {
    setRollingBack(true);
    setActionError(null);
    setMessage(null);
    try {
      await rollbackUpgrade(false);
      await mutate();
      setMessage("Rollback requested. Confirm the instance is healthy after restore.");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Rollback failed");
    } finally {
      setRollingBack(false);
    }
  };

  const alerts = data?.alerts ?? [];
  const channel = data?.channel || (data?.installable === false ? "changelog_only" : "stable");
  const historyEntries = Array.isArray(history?.entries)
    ? history.entries
    : Array.isArray(history?.history)
      ? history.history
      : [];

  return (
    <Box>
      <PageHeader
        title="Upgrade"
        description="Review available Keprix upgrades and notification preferences."
        breadcrumbs={[{ label: "Settings", href: "/settings" }, { label: "Upgrade" }]}
        actions={
          <Stack direction="row" spacing={1}>
            <Button component="a" href="/settings" variant="outlined" size="small">
              Back to settings
            </Button>
            <Button variant="contained" size="small" onClick={() => void runCheck()} disabled={checking}>
              {checking ? "Checking..." : "Check for updates"}
            </Button>
          </Stack>
        }
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error instanceof Error ? error.message : "Failed to load upgrade status"}
        </Alert>
      ) : null}
      {actionError ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setActionError(null)}>
          {actionError}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Current status
          </Typography>
          {isLoading && !data ? (
            <Typography variant="body2" color="text.secondary">
              Loading upgrade status...
            </Typography>
          ) : (
            <Stack spacing={1}>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Chip label={`Installed ${data?.current_version || "unknown"}`} color="primary" />
                <Chip
                  label={channel === "stable" ? "Stable (installable)" : channel === "changelog_only" ? "Changelog only" : "Current"}
                  color={channel === "stable" ? "success" : "default"}
                  variant="outlined"
                />
                <Chip label={`${data?.alert_count ?? 0} active alert(s)`} variant="outlined" />
              </Stack>
              <Typography variant="body2" color="text.secondary">
                Product: {data?.product || "keprix"}
                {data?.last_check_at ? ` | Last check: ${data.last_check_at}` : ""}
                {data?.latest_changelog_version ? ` | Latest listed: ${data.latest_changelog_version}` : ""}
              </Typography>
              {data?.recommendation ? (
                <Alert severity="info">{data.recommendation}</Alert>
              ) : null}
            </Stack>
          )}
        </CardContent>
      </Card>

      <Typography variant="h6" sx={{ mb: 1 }}>
        Available upgrades
      </Typography>
      {alerts.length === 0 ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          No pending upgrade alerts. Use Check for updates to poll the release channel. Banner alerts still
          appear in the workspace when a new version is available and in-app notifications are enabled.
        </Alert>
      ) : (
        <Stack spacing={1.5} sx={{ mb: 2 }}>
          {alerts.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              busy={busyAlertId === alert.id}
              onUpgrade={() => openWizard(alert.target_version)}
              onDismiss={() => void onDismiss(alert)}
              onSnooze={() => void onSnooze(alert)}
            />
          ))}
        </Stack>
      )}

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent sx={{ display: "grid", gap: 2 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" useFlexGap>
            <Typography variant="h6">Notification preferences</Typography>
            <Button variant="contained" onClick={() => void savePrefs()} disabled={savingPrefs || !prefsDirty}>
              {savingPrefs ? "Saving..." : "Save preferences"}
            </Button>
          </Stack>

          <Typography variant="subtitle2">Channels</Typography>
          <Stack spacing={1.5}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={prefs.in_app_enabled}
                    onChange={(event) => updatePref("in_app_enabled", event.target.checked)}
                  />
                }
                label="In-app banner"
              />
              <SeveritySelect
                label="Min severity"
                value={prefs.in_app_min_severity}
                onChange={(value) => updatePref("in_app_min_severity", value)}
                disabled={!prefs.in_app_enabled}
              />
            </Stack>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={prefs.email_enabled}
                    onChange={(event) => updatePref("email_enabled", event.target.checked)}
                  />
                }
                label="Email digest"
              />
              <SeveritySelect
                label="Min severity"
                value={prefs.email_min_severity}
                onChange={(value) => updatePref("email_min_severity", value)}
                disabled={!prefs.email_enabled}
              />
            </Stack>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={prefs.slack_enabled}
                    onChange={(event) => updatePref("slack_enabled", event.target.checked)}
                  />
                }
                label="Slack"
              />
              <TextField
                size="small"
                label="Slack webhook URL"
                value={prefs.slack_webhook_url}
                onChange={(event) => updatePref("slack_webhook_url", event.target.value)}
                disabled={!prefs.slack_enabled}
                sx={{ flex: 1, minWidth: 220 }}
              />
            </Stack>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={prefs.discord_enabled}
                    onChange={(event) => updatePref("discord_enabled", event.target.checked)}
                  />
                }
                label="Discord"
              />
              <TextField
                size="small"
                label="Discord webhook URL"
                value={prefs.discord_webhook_url}
                onChange={(event) => updatePref("discord_webhook_url", event.target.value)}
                disabled={!prefs.discord_enabled}
                sx={{ flex: 1, minWidth: 220 }}
              />
            </Stack>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={prefs.webhook_enabled}
                    onChange={(event) => updatePref("webhook_enabled", event.target.checked)}
                  />
                }
                label="Generic webhook"
              />
              <TextField
                size="small"
                label="Webhook URL"
                value={prefs.webhook_url}
                onChange={(event) => updatePref("webhook_url", event.target.value)}
                disabled={!prefs.webhook_enabled}
                sx={{ flex: 1, minWidth: 220 }}
              />
            </Stack>
          </Stack>

          <Divider />

          <Typography variant="subtitle2">Quiet hours</Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }}>
            <FormControlLabel
              control={
                <Switch
                  checked={prefs.quiet_hours_enabled}
                  onChange={(event) => updatePref("quiet_hours_enabled", event.target.checked)}
                />
              }
              label="Don't notify between"
            />
            <TextField
              size="small"
              type="number"
              label="Start hour"
              value={prefs.quiet_hours_start}
              onChange={(event) => updatePref("quiet_hours_start", Number(event.target.value))}
              disabled={!prefs.quiet_hours_enabled}
              inputProps={{ min: 0, max: 23 }}
              sx={{ width: 120 }}
            />
            <Typography variant="body2">and</Typography>
            <TextField
              size="small"
              type="number"
              label="End hour"
              value={prefs.quiet_hours_end}
              onChange={(event) => updatePref("quiet_hours_end", Number(event.target.value))}
              disabled={!prefs.quiet_hours_enabled}
              inputProps={{ min: 0, max: 23 }}
              sx={{ width: 120 }}
            />
          </Stack>

          <Divider />

          <Typography variant="subtitle2">Auto-upgrade</Typography>
          <FormControl size="small" sx={{ maxWidth: 360 }}>
            <InputLabel>Policy</InputLabel>
            <Select
              label="Policy"
              value={prefs.auto_upgrade_policy}
              onChange={(event) => updatePref("auto_upgrade_policy", String(event.target.value))}
            >
              <MenuItem value="manual">Manual only (recommended)</MenuItem>
              <MenuItem value="security_only">Auto-install security patches (CRITICAL)</MenuItem>
              <MenuItem value="all_updates">Auto-install all updates (not recommended)</MenuItem>
            </Select>
          </FormControl>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel>Maintenance day</InputLabel>
              <Select
                label="Maintenance day"
                value={prefs.maintenance_day}
                onChange={(event) => updatePref("maintenance_day", Number(event.target.value))}
              >
                {DAY_LABELS.map((label, index) => (
                  <MenuItem key={label} value={index}>
                    {label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              type="number"
              label="Maintenance hour (0-23)"
              value={prefs.maintenance_hour}
              onChange={(event) => updatePref("maintenance_hour", Number(event.target.value))}
              inputProps={{ min: 0, max: 23 }}
              sx={{ width: 180 }}
            />
          </Stack>
          <FormControlLabel
            control={
              <Switch
                checked={prefs.require_tests_pass}
                onChange={(event) => updatePref("require_tests_pass", event.target.checked)}
              />
            }
            label="Require dry-run / tests to pass before auto apply"
          />
          <FormControlLabel
            control={
              <Switch
                checked={prefs.notify_after_upgrade}
                onChange={(event) => updatePref("notify_after_upgrade", event.target.checked)}
              />
            }
            label="Notify after upgrade completes"
          />
        </CardContent>
      </Card>

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent sx={{ display: "grid", gap: 1.5 }}>
          <Typography variant="h6">History and rollback</Typography>
          {historyEntries.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No upgrade history recorded yet.
            </Typography>
          ) : (
            <Stack spacing={1}>
              {historyEntries.slice(0, 8).map((entry: Record<string, unknown>, index: number) => (
                <Typography key={index} variant="body2" color="text.secondary">
                  {String(entry.at || entry.timestamp || entry.created_at || "unknown time")}
                  {" | "}
                  {String(entry.action || entry.event || "upgrade")}
                  {" | "}
                  {String(entry.version || entry.target_version || entry.to || "")}
                </Typography>
              ))}
            </Stack>
          )}
          <Button
            variant="outlined"
            color="warning"
            onClick={() => void onRollback()}
            disabled={rollingBack}
            sx={{ justifySelf: "start" }}
          >
            {rollingBack ? "Rolling back..." : "Rollback last upgrade"}
          </Button>
        </CardContent>
      </Card>

      {changelog ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Latest changelog
            </Typography>
            {typeof changelog.summary === "string" ? (
              <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: "pre-wrap" }}>
                {changelog.summary}
              </Typography>
            ) : typeof changelog.markdown === "string" ? (
              <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: "pre-wrap" }}>
                {changelog.markdown}
              </Typography>
            ) : (
              <StructuredDataView value={changelog} />
            )}
          </CardContent>
        </Card>
      ) : null}

      {wizardTarget ? (
        <UpgradeWizardDialog
          open={wizardOpen}
          target={wizardTarget}
          onClose={() => setWizardOpen(false)}
          onComplete={() => void mutate()}
        />
      ) : null}
    </Box>
  );
}
