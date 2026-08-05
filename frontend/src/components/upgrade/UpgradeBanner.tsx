"use client";

import CloseIcon from "@mui/icons-material/Close";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import UpgradeWizardDialog from "@/components/upgrade/UpgradeWizardDialog";
import {
  checkUpgradeNow,
  dismissUpgradeAlert,
  fetchUpgradeStatus,
  severityColor,
  snoozeUpgradeAlert,
} from "@/lib/upgrade-api";

export default function UpgradeBanner() {
  const { data, mutate } = useSWR("keprix-upgrade-status", fetchUpgradeStatus, {
    refreshInterval: 6 * 60 * 60 * 1000,
    revalidateOnFocus: true,
    shouldRetryOnError: false,
  });
  const [wizardOpen, setWizardOpen] = React.useState(false);
  const [wizardTarget, setWizardTarget] = React.useState<string | null>(null);
  const [checking, setChecking] = React.useState(false);
  const [locallyHidden, setLocallyHidden] = React.useState(false);

  const alert = data?.alerts?.[0];
  const installable = data?.installable !== false;
  const channel = data?.channel || (installable ? "stable" : "changelog_only");
  const visible = Boolean(data?.preferences?.in_app_enabled && alert && !locallyHidden && installable);
  const autoChecked = React.useRef(false);

  React.useEffect(() => {
    if (!data || data.alert_count > 0 || autoChecked.current || locallyHidden) return;
    autoChecked.current = true;
    checkUpgradeNow()
      .then(() => mutate())
      .catch(() => undefined);
  }, [data, mutate, locallyHidden]);

  if (!visible || !alert) {
    if (data?.channel === "changelog_only" && data.recommendation && !locallyHidden) {
      return (
        <Alert severity="info" sx={{ mb: 2 }} onClose={() => setLocallyHidden(true)}>
          Release channel: changelog only. {data.recommendation}
        </Alert>
      );
    }
    return null;
  }

  const openWizard = () => {
    setWizardTarget(alert.target_version);
    setWizardOpen(true);
  };

  const dismiss = async () => {
    setLocallyHidden(true);
    setWizardOpen(false);
    try {
      await dismissUpgradeAlert(alert.id);
      await mutate();
    } catch {
      setLocallyHidden(false);
    }
  };

  const snooze = async () => {
    setLocallyHidden(true);
    setWizardOpen(false);
    try {
      await snoozeUpgradeAlert(alert.id, 24);
      await mutate();
    } catch {
      setLocallyHidden(false);
    }
  };

  const refresh = async () => {
    setChecking(true);
    try {
      await checkUpgradeNow();
      await mutate();
      setLocallyHidden(false);
    } finally {
      setChecking(false);
    }
  };

  return (
    <>
      <Paper
        variant="outlined"
        sx={{
          mb: 2,
          p: 2,
          display: "grid",
          gap: 1.5,
          borderColor: `${severityColor(alert.severity)}.main`,
        }}
      >
        <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start", flexWrap: "wrap" }}>
          <Box sx={{ flex: 1, minWidth: 240 }}>
            <Box sx={{ display: "flex", gap: 1, alignItems: "center", mb: 0.5, flexWrap: "wrap" }}>
              <Typography variant="subtitle1">{alert.title}</Typography>
              <Chip size="small" label={alert.severity.toUpperCase()} color={severityColor(alert.severity)} />
              <Chip size="small" label={`Risk ${alert.risk_level.toUpperCase()}`} variant="outlined" />
              <Chip
                size="small"
                color={channel === "stable" ? "success" : "default"}
                label={channel === "stable" ? "Stable (installable)" : "Changelog only"}
                variant="outlined"
              />
            </Box>
            <Typography variant="body2" color="text.secondary">
              {alert.summary}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
              Current: {data?.current_version} | Target: {alert.target_version} | New features: {alert.feature_count}
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
            <Button size="small" variant="outlined" onClick={() => void refresh()} disabled={checking}>
              Check again
            </Button>
            <Button size="small" variant="outlined" href="/settings/upgrade">
              Review
            </Button>
            <Button size="small" variant="contained" onClick={openWizard}>
              Upgrade now
            </Button>
            <Button size="small" onClick={() => void snooze()}>
              Later
            </Button>
            <IconButton size="small" aria-label="Dismiss upgrade alert" onClick={() => void dismiss()}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        </Box>
        {!alert.compatible ? (
          <Alert severity="warning">This upgrade is marked incompatible. Review before proceeding.</Alert>
        ) : null}
      </Paper>
      {wizardTarget ? (
        <UpgradeWizardDialog
          open={wizardOpen}
          target={wizardTarget}
          onClose={() => setWizardOpen(false)}
          onComplete={() => void mutate()}
        />
      ) : null}
    </>
  );
}
