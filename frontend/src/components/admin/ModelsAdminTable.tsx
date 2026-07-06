"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import DeleteIcon from "@mui/icons-material/Delete";
import useSWR from "swr";
import AdminTable from "@/components/admin/AdminTable";
import ConfirmDialog from "@/components/admin/ConfirmDialog";
import { SnackbarFeedback, useSnackbar } from "@/components/ui/SnackbarFeedback";
import {
  createAdminModel,
  deleteAdminModel,
  fetchAdminModels,
  patchAdminModel,
  type AdminModelRow,
} from "@/lib/admin-pages-api";

const PROVIDERS = ["anthropic", "openai", "gemini", "groq", "ollama", "openrouter"];

export default function ModelsAdminTable() {
  const { state, show, close } = useSnackbar();
  const { data, isLoading, mutate } = useSWR("admin-models-table", fetchAdminModels);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState<AdminModelRow | null>(null);
  const [provider, setProvider] = React.useState("anthropic");
  const [modelId, setModelId] = React.useState("");
  const [modelType, setModelType] = React.useState("chat");
  const [apiKey, setApiKey] = React.useState("");
  const [inputCost, setInputCost] = React.useState("");
  const [outputCost, setOutputCost] = React.useState("");
  const [enabled, setEnabled] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [optimistic, setOptimistic] = React.useState<Record<string, boolean>>({});

  const rows = (data || []).map((row) => ({
    ...row,
    enabled: optimistic[row.id] ?? row.enabled,
  }));

  const toggleEnabled = async (row: AdminModelRow, next: boolean) => {
    setOptimistic((prev) => ({ ...prev, [row.id]: next }));
    try {
      await patchAdminModel(row.id, { enabled: next });
      await mutate();
      show(next ? "Model enabled" : "Model disabled");
    } catch (err) {
      setOptimistic((prev) => {
        const copy = { ...prev };
        delete copy[row.id];
        return copy;
      });
      show(err instanceof Error ? err.message : "Update failed", "error");
    }
  };

  const handleCreate = async () => {
    if (!modelId.trim()) {
      show("Model ID is required", "error");
      return;
    }
    setBusy(true);
    try {
      await createAdminModel({
        provider,
        model_id: modelId.trim(),
        type: modelType,
        api_key: apiKey || undefined,
        input_cost_per_m: inputCost ? Number(inputCost) : undefined,
        output_cost_per_m: outputCost ? Number(outputCost) : undefined,
        enabled,
      });
      await mutate();
      setDialogOpen(false);
      show("Model added");
    } catch (err) {
      show(err instanceof Error ? err.message : "Failed to add model", "error");
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { id: "provider", label: "Provider" },
    { id: "model_id", label: "Model ID" },
    {
      id: "type",
      label: "Type",
      render: (row: AdminModelRow) => <Chip size="small" label={row.type} variant="outlined" />,
    },
    {
      id: "enabled",
      label: "Enabled",
      render: (row: AdminModelRow) => (
        <Switch
          size="small"
          checked={row.enabled}
          onChange={(e) => void toggleEnabled(row, e.target.checked)}
          onClick={(e) => e.stopPropagation()}
        />
      ),
    },
    { id: "priority", label: "Priority", width: 80 },
    {
      id: "actions",
      label: "",
      width: 60,
      render: (row: AdminModelRow) => (
        <IconButton size="small" onClick={(e) => { e.stopPropagation(); setDeleteTarget(row); }}>
          <DeleteIcon fontSize="small" />
        </IconButton>
      ),
    },
  ];

  return (
    <>
      <AdminTable
        title="Configured models"
        columns={columns}
        rows={rows}
        loading={isLoading}
        action={
          <Button size="small" variant="contained" onClick={() => setDialogOpen(true)}>
            Add model
          </Button>
        }
      />

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add model</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField select label="Provider" value={provider} onChange={(e) => setProvider(e.target.value)} fullWidth>
            {PROVIDERS.map((item) => (
              <MenuItem key={item} value={item}>
                {item}
              </MenuItem>
            ))}
          </TextField>
          <TextField label="Model ID" value={modelId} onChange={(e) => setModelId(e.target.value)} fullWidth />
          <TextField select label="Type" value={modelType} onChange={(e) => setModelType(e.target.value)} fullWidth>
            <MenuItem value="chat">Chat</MenuItem>
            <MenuItem value="embed">Embed</MenuItem>
          </TextField>
          <TextField
            label="API key"
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            fullWidth
          />
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
            <TextField
              label="Input cost / 1M tokens"
              type="number"
              value={inputCost}
              onChange={(e) => setInputCost(e.target.value)}
            />
            <TextField
              label="Output cost / 1M tokens"
              type="number"
              value={outputCost}
              onChange={(e) => setOutputCost(e.target.value)}
            />
          </Box>
          <FormControlLabel
            control={<Switch checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />}
            label="Enabled"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} disabled={busy}>
            Cancel
          </Button>
          <Button variant="contained" onClick={() => void handleCreate()} disabled={busy}>
            Add
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete model"
        body={`Remove configuration for "${deleteTarget?.model_id}"?`}
        onClose={() => setDeleteTarget(null)}
        onConfirm={async () => {
          if (!deleteTarget) return;
          await deleteAdminModel(deleteTarget.id);
          await mutate();
          setDeleteTarget(null);
          show("Model removed");
        }}
      />
      <SnackbarFeedback state={state} onClose={close} />
    </>
  );
}
