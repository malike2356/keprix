"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import { fetchCrmDeliverability, fetchCrmKillSwitches, upsertCrmKillSwitch } from "@/lib/crm-api";

const WORKSPACE = "default";

export default function OutreachSettingsPage() {
  const switches = useSWR(["crm-kill-switches", WORKSPACE], () => fetchCrmKillSwitches(WORKSPACE));
  const deliverability = useSWR(["crm-deliverability", WORKSPACE], () => fetchCrmDeliverability(WORKSPACE));
  const [scope, setScope] = React.useState("workspace");
  const [scopeId, setScopeId] = React.useState("");
  const [enabled, setEnabled] = React.useState(true);
  const [reason, setReason] = React.useState("");
  const [quietHours, setQuietHours] = React.useState("22:00-07:00");
  const [timezone, setTimezone] = React.useState("Europe/London");
  const [maxPerWeek, setMaxPerWeek] = React.useState("3");
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg] = React.useState<string | null>(null);
  const [err, setErr] = React.useState<string | null>(null);

  const items = switches.data?.items ?? [];
  const workspaceOn = items.some((s) => s.scope === "workspace" && s.enabled);

  const saveSwitch = async () => {
    setBusy(true);
    setErr(null);
    try {
      const result = await upsertCrmKillSwitch(
        {
          scope,
          scope_id: scopeId.trim() || null,
          enabled,
          reason: reason.trim() || undefined,
        },
        WORKSPACE,
      );
      if (result.blocked) {
        setMsg("Soft Wall approval required to turn kill switch OFF. See Approvals.");
      } else {
        setMsg(enabled ? "Kill switch enabled (sends blocked for scope)" : "Kill switch disabled");
      }
      await switches.mutate();
      await deliverability.mutate();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
      {switches.error || err ? (
        <Alert severity="error" onClose={() => setErr(null)}>
          {switches.error instanceof Error ? switches.error.message : err}
        </Alert>
      ) : null}
      {msg ? (
        <Alert severity="success" onClose={() => setMsg(null)}>
          {msg}
        </Alert>
      ) : null}

      {workspaceOn ? (
        <Alert severity="error">
          Workspace Soft Wall kill switch is ON. Outbound Soft Wall sends should stop.{" "}
          <Button component={NextLink} href="/outreach/deliverability" size="small">
            Deliverability
          </Button>
        </Alert>
      ) : (
        <Alert severity="info">Workspace kill switch is off. Turning it off again still requires Soft Wall.</Alert>
      )}

      <Typography variant="body2" color="text.secondary">
        Kill switches stop Soft Wall sends immediately when enabled. Disabling a kill switch or raising budgets
        requires Soft Wall approval. Cadence fields below are operator notes until campaign budgets wire fully.
      </Typography>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Kill switches
        </Typography>
        {items.length === 0 ? (
          <EmptyState title="No kill switches configured" description="Enable a workspace or campaign scope kill switch when needed." />
        ) : (
          <Stack spacing={1} sx={{ mb: 2 }}>
            {items.map((row) => (
              <Typography key={String(row.id)} variant="body2">
                {String(row.scope)}
                {row.scope_id ? `:${row.scope_id}` : ""}; {row.enabled ? "ON (blocking)" : "off"};{" "}
                {String(row.reason || "")}
              </Typography>
            ))}
          </Stack>
        )}
        <Stack spacing={1}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel id="scope">Scope</InputLabel>
              <Select labelId="scope" label="Scope" value={scope} onChange={(e) => setScope(String(e.target.value))}>
                {["workspace", "campaign", "domain"].map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Scope ID (campaign/domain)"
              value={scopeId}
              onChange={(e) => setScopeId(e.target.value)}
              sx={{ flex: 1 }}
            />
            <FormControlLabel
              control={<Switch checked={enabled} onChange={(_, v) => setEnabled(v)} />}
              label={enabled ? "Blocking ON" : "Blocking OFF"}
            />
          </Stack>
          <TextField size="small" label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} fullWidth />
          <Button variant="contained" disabled={busy} onClick={() => void saveSwitch()}>
            Save kill switch
          </Button>
        </Stack>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Cadence / quiet hours (operator policy notes)
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <TextField size="small" label="Quiet hours" value={quietHours} onChange={(e) => setQuietHours(e.target.value)} />
          <TextField size="small" label="Timezone" value={timezone} onChange={(e) => setTimezone(e.target.value)} />
          <TextField
            size="small"
            label="Max emails/week/contact"
            value={maxPerWeek}
            onChange={(e) => setMaxPerWeek(e.target.value)}
          />
        </Stack>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
          Stored locally in the browser for operators until campaign budget APIs land. Raising send budgets above
          policy still uses Soft Wall gate kind budget_raise.
        </Typography>
      </Paper>

      {deliverability.data?.breaches?.length ? (
        <Alert severity="warning">
          Deliverability breaches: {deliverability.data.breaches.join("; ")}. Cold Soft Wall approve should stay blocked.
        </Alert>
      ) : null}
    </Stack>
  );
}
