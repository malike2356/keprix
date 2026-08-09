"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { OutreachControlState } from "@/components/outreach/types";
import type { OutreachSchedulerHealth } from "@/lib/outreach-api";

type ControlCenterProps = {
  control: OutreachControlState | null;
  schedulerHealth?: OutreachSchedulerHealth | null;
  busy?: boolean;
  error?: string | null;
  onProcessDue: () => void;
  onTogglePause: () => void;
  approvalsHref?: string;
};

function formatAge(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) return "n/a";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h`;
}

export function ControlCenter({
  control,
  schedulerHealth,
  busy,
  error,
  onProcessDue,
  onTogglePause,
  approvalsHref = "/outreach/approvals",
}: ControlCenterProps) {
  const paused = Boolean(control?.paused);
  const updatedAt = control?.updated_at || control?.updatedAt;
  const queueDepth = Number(schedulerHealth?.queue_depth ?? 0);
  const deadLetters = Number(schedulerHealth?.dead_letter_count ?? 0);
  const oldest = schedulerHealth?.oldest_due_age_seconds;

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={2}
          alignItems={{ xs: "stretch", md: "flex-start" }}
          justifyContent="space-between"
        >
          <Box>
            <Typography variant="overline" color="text.secondary">
              Outreach control center
            </Typography>
            <Typography variant="h5" component="h2" sx={{ mt: 0.25 }}>
              Sales engagement
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1, maxWidth: 640 }}>
              Manage lead intake, campaign pacing, sequences, Soft Wall approvals, replies, bookings,
              and registry ingest from one surface. No mass-send without approval.
            </Typography>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }}>
              <Chip
                size="small"
                label={paused ? "Paused" : "Active"}
                color={paused ? "warning" : "success"}
                variant="outlined"
              />
              {schedulerHealth ? (
                <>
                  <Chip
                    size="small"
                    variant="outlined"
                    label={`Queue ${queueDepth}`}
                    color={queueDepth > 0 ? "info" : "default"}
                  />
                  <Chip
                    size="small"
                    variant="outlined"
                    label={`Dead letters ${deadLetters}`}
                    color={deadLetters > 0 ? "warning" : "default"}
                  />
                  <Chip
                    size="small"
                    variant="outlined"
                    label={`Oldest due ${formatAge(oldest)}`}
                  />
                </>
              ) : null}
              {control?.reason ? (
                <Typography variant="caption" color="text.secondary">
                  {control.reason}
                </Typography>
              ) : null}
              {updatedAt ? (
                <Typography variant="caption" color="text.secondary">
                  Updated {new Date(updatedAt).toLocaleString()}
                </Typography>
              ) : null}
            </Stack>
          </Box>

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button size="small" variant="contained" disabled={busy} onClick={onProcessDue}>
              Process due
            </Button>
            <Button size="small" variant="outlined" disabled={busy || !control} onClick={onTogglePause}>
              {paused ? "Resume outreach" : "Pause outreach"}
            </Button>
            <Button size="small" variant="outlined" component="a" href={approvalsHref}>
              Open Approvals
            </Button>
          </Stack>
        </Stack>

        {error ? (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default ControlCenter;
