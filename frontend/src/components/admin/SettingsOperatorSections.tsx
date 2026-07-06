"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { SnackbarFeedback, useSnackbar } from "@/components/ui/SnackbarFeedback";
import type { AdminSettings } from "@/lib/admin-workspace-api";
import { saveAdminSettingsPayload } from "@/lib/admin-pages-api";

type SettingsOperatorSectionsProps = {
  settings: AdminSettings;
  modelOptions: string[];
  onSaved: () => void;
};

const PERSONAS = ["beacon", "compass", "codex", "scout", "default"];

export default function SettingsOperatorSections({
  settings: initial,
  modelOptions,
  onSaved,
}: SettingsOperatorSectionsProps) {
  const { state, show, close } = useSnackbar();
  const [settings, setSettings] = React.useState(initial);
  const [authEnabled, setAuthEnabled] = React.useState(true);
  const [sessionHours, setSessionHours] = React.useState(24);
  const [require2fa, setRequire2fa] = React.useState(false);
  const [defaultModel, setDefaultModel] = React.useState(modelOptions[0] || "");
  const [defaultPersona, setDefaultPersona] = React.useState("beacon");
  const [maxTokens, setMaxTokens] = React.useState(4096);
  const [maxAgents, setMaxAgents] = React.useState(4);
  const [defaultWorkspaceId, setDefaultWorkspaceId] = React.useState("default");
  const [toolSynthesisEnabled, setToolSynthesisEnabled] = React.useState(true);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    setSettings(initial);
    setDefaultModel(modelOptions[0] || "");
  }, [initial, modelOptions]);

  const patch = <K extends keyof AdminSettings>(key: K, value: AdminSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setBusy(true);
    try {
      const payload: AdminSettings = {
        ...settings,
        mutation_engine_enabled: settings.mutation_engine_enabled,
        mutation_sandbox_timeout: settings.mutation_sandbox_timeout,
        auto_approve_owner_mutations: settings.auto_approve_owner_mutations,
        max_tool_iterations: settings.max_tool_iterations,
      };
      await saveAdminSettingsPayload(payload);
      show("Settings saved");
      onSaved();
    } catch (err) {
      show(err instanceof Error ? err.message : "Failed to save settings", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Instance
        </Typography>
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
          <TextField
            label="Instance name"
            value={settings.instance_name}
            onChange={(e) => patch("instance_name", e.target.value)}
            fullWidth
          />
          <TextField
            label="Default workspace ID"
            value={defaultWorkspaceId}
            onChange={(e) => setDefaultWorkspaceId(e.target.value)}
            fullWidth
          />
          <TextField
            label="Max concurrent agents"
            type="number"
            inputProps={{ min: 1, max: 32 }}
            value={maxAgents}
            onChange={(e) => setMaxAgents(Number(e.target.value))}
            fullWidth
          />
        </Box>
      </Box>

      <Divider />

      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Security
        </Typography>
        <Box sx={{ display: "grid", gap: 1 }}>
          <FormControlLabel
            control={<Switch checked={authEnabled} onChange={(e) => setAuthEnabled(e.target.checked)} />}
            label="Auth enabled"
          />
          <TextField
            label="Session duration (hours)"
            type="number"
            value={sessionHours}
            onChange={(e) => setSessionHours(Number(e.target.value))}
            sx={{ maxWidth: 280 }}
          />
          <FormControlLabel
            control={<Switch checked={require2fa} onChange={(e) => setRequire2fa(e.target.checked)} />}
            label="Require 2FA"
          />
        </Box>
      </Box>

      <Divider />

      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Defaults
        </Typography>
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
          <TextField select label="Default LLM model" value={defaultModel} onChange={(e) => setDefaultModel(e.target.value)} fullWidth>
            {modelOptions.map((model) => (
              <MenuItem key={model} value={model}>
                {model}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Default persona"
            value={defaultPersona}
            onChange={(e) => setDefaultPersona(e.target.value)}
            fullWidth
          >
            {PERSONAS.map((persona) => (
              <MenuItem key={persona} value={persona}>
                {persona}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Max tokens per response"
            type="number"
            value={maxTokens}
            onChange={(e) => setMaxTokens(Number(e.target.value))}
            fullWidth
          />
        </Box>
      </Box>

      <Divider />

      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Mutation engine
        </Typography>
        <Box sx={{ display: "grid", gap: 1 }}>
          <FormControlLabel
            control={
              <Switch
                checked={settings.mutation_engine_enabled}
                onChange={(e) => patch("mutation_engine_enabled", e.target.checked)}
              />
            }
            label="Mutation engine enabled"
          />
          <FormControlLabel
            control={<Switch checked={toolSynthesisEnabled} onChange={(e) => setToolSynthesisEnabled(e.target.checked)} />}
            label="Tool synthesis enabled"
          />
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.auto_approve_owner_mutations}
                  onChange={(e) => patch("auto_approve_owner_mutations", e.target.checked)}
                />
              }
              label="Auto-approve mutations"
            />
            {settings.auto_approve_owner_mutations ? (
              <Chip size="small" color="warning" label="Dangerous" />
            ) : null}
          </Box>
          <TextField
            label="Sandbox timeout (seconds)"
            type="number"
            value={settings.mutation_sandbox_timeout}
            onChange={(e) => patch("mutation_sandbox_timeout", Number(e.target.value))}
            sx={{ maxWidth: 280 }}
          />
        </Box>
      </Box>

      <Box>
        <Button variant="contained" onClick={() => void handleSave()} disabled={busy}>
          Save operator settings
        </Button>
      </Box>

      <SnackbarFeedback state={state} onClose={close} />
    </Box>
  );
}
