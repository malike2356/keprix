"use client";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import PendingIcon from "@mui/icons-material/Pending";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  dryRunUpgrade,
  executeUpgrade,
  fetchUpgradeWizard,
  type UpgradeDryRunResult,
  type UpgradeWizardStep,
} from "@/lib/upgrade-api";

type Props = {
  open: boolean;
  target: string;
  onClose: () => void;
  onComplete: () => void;
};

type WizardStage = "review" | "dry-run" | "confirm" | "executing" | "done" | "failed";

function stepIcon(status: UpgradeWizardStep["status"]) {
  switch (status) {
    case "done":
      return <CheckCircleIcon color="success" fontSize="small" />;
    case "failed":
      return <ErrorIcon color="error" fontSize="small" />;
    case "running":
      return <CircularProgress size={16} />;
    default:
      return <PendingIcon color="disabled" fontSize="small" />;
  }
}

export default function UpgradeWizardDialog({ open, target, onClose, onComplete }: Props) {
  const [stage, setStage] = React.useState<WizardStage>("review");
  const [steps, setSteps] = React.useState<UpgradeWizardStep[]>([]);
  const [dryRun, setDryRun] = React.useState<UpgradeDryRunResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!open) return;
    setStage("review");
    setDryRun(null);
    setError(null);
    setLoading(true);
    fetchUpgradeWizard(target)
      .then((payload) => setSteps(payload.steps || []))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load upgrade plan"))
      .finally(() => setLoading(false));
  }, [open, target]);

  const runDryRun = async () => {
    setStage("dry-run");
    setLoading(true);
    setError(null);
    try {
      const result = await dryRunUpgrade(target);
      setDryRun(result);
      setStage("confirm");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dry run failed");
      setStage("review");
    } finally {
      setLoading(false);
    }
  };

  const runExecute = async () => {
    setStage("executing");
    setLoading(true);
    setError(null);
    try {
      const result = await executeUpgrade(target);
      if (result.success) {
        setStage("done");
        onComplete();
      } else {
        setError(result.error || "Upgrade failed");
        setStage("failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upgrade failed");
      setStage("failed");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (stage === "executing") return;
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle>Upgrade to {target}</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2 }}>
        {error ? <Alert severity="error">{error}</Alert> : null}

        {stage === "review" ? (
          <>
            <Typography variant="body2" color="text.secondary">
              Planned upgrade steps. Run a dry run first to validate compatibility before applying.
            </Typography>
            {loading ? (
              <Stack alignItems="center" sx={{ py: 3 }}>
                <CircularProgress size={24} />
              </Stack>
            ) : (
              <List dense>
                {steps.map((step) => (
                  <ListItem key={step.id} disableGutters>
                    <ListItemIcon sx={{ minWidth: 32 }}>{stepIcon(step.status)}</ListItemIcon>
                    <ListItemText primary={step.label} secondary={step.detail} />
                  </ListItem>
                ))}
              </List>
            )}
          </>
        ) : null}

        {stage === "dry-run" ? (
          <Stack alignItems="center" spacing={1} sx={{ py: 3 }}>
            <CircularProgress size={24} />
            <Typography variant="body2" color="text.secondary">
              Running compatibility checks...
            </Typography>
          </Stack>
        ) : null}

        {stage === "confirm" && dryRun ? (
          <Box sx={{ display: "grid", gap: 1.5 }}>
            <Alert severity={dryRun.passed ? "success" : "warning"}>
              {dryRun.passed_tests}/{dryRun.total_tests} checks passed in {dryRun.duration_seconds.toFixed(1)}s
            </Alert>
            {dryRun.warnings.length > 0 ? (
              <Box>
                <Typography variant="subtitle2">Warnings</Typography>
                {dryRun.warnings.map((warning, index) => (
                  <Typography key={index} variant="body2" color="text.secondary">
                    - {warning}
                  </Typography>
                ))}
              </Box>
            ) : null}
            {dryRun.failed_test_details.length > 0 ? (
              <Box>
                <Typography variant="subtitle2" color="error">
                  Failed checks
                </Typography>
                {dryRun.failed_test_details.map((detail, index) => (
                  <Typography key={index} variant="body2" color="text.secondary">
                    - {detail}
                  </Typography>
                ))}
              </Box>
            ) : null}
            <Typography variant="body2">{dryRun.recommendation}</Typography>
          </Box>
        ) : null}

        {stage === "executing" ? (
          <Stack alignItems="center" spacing={1} sx={{ py: 3 }}>
            <CircularProgress size={24} />
            <Typography variant="body2" color="text.secondary">
              Applying upgrade to {target}. This may take a moment.
            </Typography>
          </Stack>
        ) : null}

        {stage === "done" ? (
          <Alert severity="success" icon={<CheckCircleIcon fontSize="inherit" />}>
            Upgrade to {target} completed.
          </Alert>
        ) : null}

        {stage === "failed" ? (
          <Alert severity="error" icon={<HourglassEmptyIcon fontSize="inherit" />}>
            Upgrade did not complete. Review the error above before retrying.
          </Alert>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={stage === "executing"}>
          {stage === "done" ? "Close" : "Cancel"}
        </Button>
        {stage === "review" ? (
          <Button variant="outlined" onClick={() => void runDryRun()} disabled={loading}>
            Run dry run
          </Button>
        ) : null}
        {stage === "confirm" ? (
          <Button variant="contained" onClick={() => void runExecute()} disabled={loading}>
            Apply upgrade
          </Button>
        ) : null}
        {stage === "failed" ? (
          <Button variant="outlined" onClick={() => void runDryRun()} disabled={loading}>
            Retry dry run
          </Button>
        ) : null}
      </DialogActions>
    </Dialog>
  );
}
