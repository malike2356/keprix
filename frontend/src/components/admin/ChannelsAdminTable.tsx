"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Step from "@mui/material/Step";
import StepLabel from "@mui/material/StepLabel";
import Stepper from "@mui/material/Stepper";
import TextField from "@mui/material/TextField";
import DeleteIcon from "@mui/icons-material/Delete";
import useSWR from "swr";
import AdminTable from "@/components/admin/AdminTable";
import ConfirmDialog from "@/components/admin/ConfirmDialog";
import { SnackbarFeedback, useSnackbar } from "@/components/ui/SnackbarFeedback";
import {
  createAdminChannel,
  deleteAdminChannel,
  fetchAdminChannels,
  type AdminChannelRow,
} from "@/lib/admin-pages-api";
import { formatTimeAgo } from "@/lib/time-ago";

const CHANNEL_TYPES = ["telegram", "discord", "slack", "whatsapp", "email", "webhook"];

function statusChip(status: string) {
  if (status === "healthy" || status === "connected" || status === "active") {
    return <Chip size="small" color="success" label={status} />;
  }
  if (status === "error" || status === "degraded") {
    return <Chip size="small" color="error" label={status} />;
  }
  return <Chip size="small" color="default" label={status || "disconnected"} />;
}

export default function ChannelsAdminTable() {
  const { state, show, close } = useSnackbar();
  const { data, isLoading, mutate } = useSWR("admin-channels-table", fetchAdminChannels);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [step, setStep] = React.useState(0);
  const [channelType, setChannelType] = React.useState("telegram");
  const [name, setName] = React.useState("");
  const [token, setToken] = React.useState("");
  const [deleteTarget, setDeleteTarget] = React.useState<AdminChannelRow | null>(null);
  const [busy, setBusy] = React.useState(false);

  const resetDialog = () => {
    setStep(0);
    setChannelType("telegram");
    setName("");
    setToken("");
  };

  const handleCreate = async () => {
    setBusy(true);
    try {
      await createAdminChannel({
        type: channelType,
        name: name || channelType,
        credentials: { token },
      });
      await mutate();
      setDialogOpen(false);
      resetDialog();
      show("Channel saved");
    } catch (err) {
      show(err instanceof Error ? err.message : "Failed to add channel", "error");
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { id: "type", label: "Type" },
    { id: "name", label: "Name" },
    {
      id: "status",
      label: "Status",
      render: (row: AdminChannelRow) => statusChip(row.status),
    },
    {
      id: "last_event_at",
      label: "Last event",
      render: (row: AdminChannelRow) =>
        row.last_event_at ? formatTimeAgo(row.last_event_at) || row.last_event_at : "Never",
    },
    {
      id: "actions",
      label: "",
      width: 120,
      render: (row: AdminChannelRow) => (
        <Box sx={{ display: "flex", gap: 0.5 }}>
          {row.status === "error" || row.status === "disconnected" || row.status === "degraded" ? (
            <Button
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                show("Use the channel cards above to reconnect", "info");
              }}
            >
              Reconnect
            </Button>
          ) : null}
          <IconButton size="small" onClick={(e) => { e.stopPropagation(); setDeleteTarget(row); }}>
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Box>
      ),
    },
  ];

  return (
    <>
      <AdminTable
        title="Channel registry"
        columns={columns}
        rows={data || []}
        loading={isLoading}
        action={
          <Button
            size="small"
            variant="contained"
            onClick={() => {
              resetDialog();
              setDialogOpen(true);
            }}
          >
            Add channel
          </Button>
        }
      />

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add channel</DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          <Stepper activeStep={step} sx={{ mb: 3 }}>
            <Step>
              <StepLabel>Type</StepLabel>
            </Step>
            <Step>
              <StepLabel>Credentials</StepLabel>
            </Step>
          </Stepper>
          {step === 0 ? (
            <TextField
              select
              label="Channel type"
              value={channelType}
              onChange={(e) => setChannelType(e.target.value)}
              fullWidth
            >
              {CHANNEL_TYPES.map((type) => (
                <MenuItem key={type} value={type}>
                  {type}
                </MenuItem>
              ))}
            </TextField>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <TextField label="Display name" value={name} onChange={(e) => setName(e.target.value)} fullWidth />
              <TextField
                label={channelType === "email" ? "IMAP password" : "Bot token / secret"}
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                fullWidth
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} disabled={busy}>
            Cancel
          </Button>
          {step > 0 ? (
            <Button onClick={() => setStep(0)} disabled={busy}>
              Back
            </Button>
          ) : null}
          {step === 0 ? (
            <Button variant="contained" onClick={() => setStep(1)}>
              Next
            </Button>
          ) : (
            <Button variant="contained" onClick={() => void handleCreate()} disabled={busy}>
              Save
            </Button>
          )}
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete channel"
        body={`Remove "${deleteTarget?.name}" from the registry?`}
        onClose={() => setDeleteTarget(null)}
        onConfirm={async () => {
          if (!deleteTarget) return;
          await deleteAdminChannel(deleteTarget.id);
          await mutate();
          setDeleteTarget(null);
          show("Channel removed");
        }}
      />
      <SnackbarFeedback state={state} onClose={close} />
    </>
  );
}
