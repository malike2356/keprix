"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import type { OutreachControlState } from "@/components/outreach/types";

type ControlCenterProps = {
  control: OutreachControlState | null;
  busy?: boolean;
  error?: string | null;
  onProcessDue: () => void;
  onTogglePause: () => void;
  approvalsHref?: string;
};

export function ControlCenter({
  control,
  busy,
  error,
  onProcessDue,
  onTogglePause,
  approvalsHref = "/outreach/approvals",
}: ControlCenterProps) {
  const paused = Boolean(control?.paused);
  const updatedAt = control?.updated_at || control?.updatedAt;

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
            <Button size="small" variant="outlined" component={Link} href={approvalsHref}>
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
