"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import {
  WAKE_WORD_MAX_COUNT,
  WAKE_WORD_MAX_LENGTH,
  fetchWakeNodes,
  fetchWakeWords,
  isWebWakeUnavailable,
  resetWakeWords,
  saveWakeRouting,
  saveWakeWords,
} from "@/lib/voice-wake-api";

export default function WakeWordsSettingsPage() {
  const { data, mutate } = useSWR("wake-words", fetchWakeWords);
  const { data: nodesData } = useSWR("wake-nodes", fetchWakeNodes);
  const [triggers, setTriggers] = React.useState<string[]>([]);
  const [newTrigger, setNewTrigger] = React.useState("");
  const [routingMode, setRoutingMode] = React.useState("current");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    if (!data) return;
    setTriggers(data.triggers);
    setRoutingMode(data.routing.default_target.mode || "current");
  }, [data]);

  const handleAdd = () => {
    const value = newTrigger.trim().toLowerCase();
    if (!value || value.length > WAKE_WORD_MAX_LENGTH) return;
    if (triggers.includes(value)) return;
    if (triggers.length >= WAKE_WORD_MAX_COUNT) return;
    setTriggers((current) => [...current, value]);
    setNewTrigger("");
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await saveWakeWords(triggers);
      await saveWakeRouting({
        version: 1,
        default_target: { mode: routingMode },
        device_targets: data?.routing.device_targets ?? {},
      });
      await mutate();
      setMessage("Saved. Changes will take effect on all your connected devices.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    setSaving(true);
    setError(null);
    try {
      const result = await resetWakeWords();
      setTriggers(result.triggers);
      await mutate();
      setMessage("Reset to default wake words.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setSaving(false);
    }
  };

  const nodes = nodesData?.nodes ?? [];
  const showRouting = nodes.length > 1;

  return (
    <Box>
      <PageHeader
        title="Wake words"
        description="Gateway-owned trigger phrases shared across desktop and mobile nodes."
      />
      <Alert severity="info" sx={{ mb: 2 }}>
        Wake word detection is unavailable in the web app and CLI. Enable it on desktop or mobile devices.
      </Alert>
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Trigger phrases</Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1, mb: 2 }}>
            {triggers.map((trigger, index) => (
              <Box key={`${trigger}-${index}`} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Chip label={trigger} />
                <IconButton
                  aria-label={`Delete ${trigger}`}
                  onClick={() => setTriggers((current) => current.filter((_, i) => i !== index))}
                >
                  <DeleteOutlineIcon fontSize="small" />
                </IconButton>
              </Box>
            ))}
          </Box>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
            <TextField
              label="Add trigger"
              value={newTrigger}
              inputProps={{ maxLength: WAKE_WORD_MAX_LENGTH }}
              onChange={(event) => setNewTrigger(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  handleAdd();
                }
              }}
            />
            <Button variant="outlined" onClick={handleAdd} disabled={triggers.length >= WAKE_WORD_MAX_COUNT}>
              Add
            </Button>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {triggers.length}/{WAKE_WORD_MAX_COUNT} phrases. Defaults: keprix, hey keprix.
          </Typography>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button variant="contained" disabled={saving} onClick={handleSave}>Save</Button>
            <Button variant="outlined" disabled={saving} onClick={handleReset}>Reset defaults</Button>
          </Box>
        </CardContent>
      </Card>

      {showRouting ? (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>Routing</Typography>
            <FormControl>
              <RadioGroup value={routingMode} onChange={(event) => setRoutingMode(event.target.value)}>
                <FormControlLabel value="current" control={<Radio />} label="Current device" />
                <FormControlLabel value="specific_node" control={<Radio />} label="Always desktop" />
                <FormControlLabel value="active_session" control={<Radio />} label="Active session" />
              </RadioGroup>
            </FormControl>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Connected nodes</Typography>
          {nodes.length === 0 ? (
            <Typography variant="body2">No connected nodes reported yet.</Typography>
          ) : (
            nodes.map((node) => (
              <Box key={node.node_id} sx={{ mb: 1 }}>
                <Typography variant="subtitle2">{node.node_id} ({node.platform})</Typography>
                <Typography variant="body2" color="text.secondary">
                  Wake enabled: {node.wake_enabled ? "yes" : "no"}.
                  Permission: {node.permission_granted ? "granted" : "denied"}.
                  {isWebWakeUnavailable(node.platform) ? " Detection unavailable on this platform." : ""}
                </Typography>
              </Box>
            ))
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
