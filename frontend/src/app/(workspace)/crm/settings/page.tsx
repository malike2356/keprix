"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import {
  approveCrmApproval,
  deleteCrmConnectionCredential,
  fetchCrmConnections,
  fetchCrmDemoSeedStatus,
  fetchCrmSettingsSummary,
  purgeCrmDemoSeed,
  putCrmConnectionCredential,
  putCrmConnectionFlag,
  upsertCrmKillSwitch,
  type CrmConnectionFlagStatus,
  type CrmConnectionSlotStatus,
} from "@/lib/crm-api";

const GROUP_LABELS: Record<string, string> = {
  crm_integrations: "CRM integrations (HubSpot, Salesforce, Pipedrive, GHL)",
  enrichment: "Licensed enrichment",
  messaging: "WhatsApp / SMS",
  social: "Social APIs (LinkedIn, Meta, TikTok)",
  property_portals: "Property portals (licensed feeds)",
};

function ConnectionsPanel() {
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [drafts, setDrafts] = React.useState<Record<string, string>>({});
  const [saving, setSaving] = React.useState<string | null>(null);
  const conn = useSWR(["crm-connections", CRM_WORKSPACE], () => fetchCrmConnections(CRM_WORKSPACE));

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.location.hash === "#connections") {
      document.getElementById("connections")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [conn.data]);

  const saveSlot = async (slotId: string) => {
    const value = (drafts[slotId] || "").trim();
    if (!value) {
      setError("Enter a value before saving.");
      return;
    }
    setError(null);
    setSaving(slotId);
    try {
      await putCrmConnectionCredential({ slot_id: slotId, value }, CRM_WORKSPACE);
      setDrafts((prev) => ({ ...prev, [slotId]: "" }));
      setMessage(`Saved ${slotId} (encrypted at rest; plaintext never returned).`);
      await conn.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(null);
    }
  };

  const clearSlot = async (slotId: string) => {
    setError(null);
    setSaving(slotId);
    try {
      await deleteCrmConnectionCredential(slotId, CRM_WORKSPACE);
      setMessage(`Cleared workspace value for ${slotId}. Env fallback still applies if set.`);
      await conn.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setSaving(null);
    }
  };

  const toggleFlag = async (flag: CrmConnectionFlagStatus, enabled: boolean) => {
    setError(null);
    try {
      await putCrmConnectionFlag({ flag_id: flag.flag_id, enabled }, CRM_WORKSPACE);
      setMessage(`${flag.label}: ${enabled ? "enabled" : "disabled"}`);
      await conn.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Flag update failed");
    }
  };

  const groups = conn.data?.status?.groups || {};
  const flags = conn.data?.status?.flags || [];
  const groupOrder = ["crm_integrations", "enrichment", "messaging", "social", "property_portals"];

  return (
    <Stack id="connections" spacing={2} sx={{ scrollMarginTop: 96 }}>
      <Typography variant="h6">Connections</Typography>
      <Typography variant="body2" color="text.secondary">
        Enter API keys, tokens, and feature flags for CRM integrations, licensed enrichment, WhatsApp/SMS,
        social APIs, and property portals. Values are encrypted at rest. Status APIs only show masked last4.
        Process env vars remain a fallback for ops deploys.
      </Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}
      {conn.error ? (
        <Alert severity="error">{conn.error instanceof Error ? conn.error.message : "Load failed"}</Alert>
      ) : null}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1">Feature flags</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Turn adapters on for this workspace. Soft Wall still gates first sends / risky actions.
          </Typography>
          <Stack spacing={0.5}>
            {flags.map((flag) => (
              <FormControlLabel
                key={flag.flag_id}
                control={
                  <Switch
                    checked={Boolean(flag.enabled)}
                    onChange={(e) => void toggleFlag(flag, e.target.checked)}
                    size="small"
                  />
                }
                label={
                  <Stack spacing={0}>
                    <Typography variant="body2">{flag.label}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {flag.description}
                      {flag.env_enabled ? " (also on via env)" : ""}
                    </Typography>
                  </Stack>
                }
              />
            ))}
          </Stack>
        </CardContent>
      </Card>

      {groupOrder.map((groupId) => {
        const slots = (groups[groupId] || []) as CrmConnectionSlotStatus[];
        if (!slots.length) return null;
        return (
          <Card key={groupId} variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <Typography variant="subtitle1">{GROUP_LABELS[groupId] || groupId}</Typography>
                <Chip
                  size="small"
                  label={conn.data?.status?.ready_groups?.[groupId] ? "ready" : "needs keys"}
                  color={conn.data?.status?.ready_groups?.[groupId] ? "success" : "default"}
                  variant="outlined"
                />
              </Stack>
              <Stack spacing={2}>
                {slots.map((slot) => (
                  <Stack key={slot.slot_id} spacing={0.75}>
                    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                      <Typography variant="body2" fontWeight={600}>
                        {slot.label}
                      </Typography>
                      <Chip
                        size="small"
                        label={
                          slot.configured
                            ? `configured (${slot.source || "unknown"}${slot.masked ? `: ${slot.masked}` : ""})`
                            : "not configured"
                        }
                        color={slot.configured ? "success" : "warning"}
                        variant="outlined"
                      />
                    </Stack>
                    <Typography variant="caption" color="text.secondary">
                      {slot.description}
                    </Typography>
                    <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems="flex-start">
                      <TextField
                        size="small"
                        fullWidth
                        type={slot.secret ? "password" : "text"}
                        label={slot.configured ? "Replace value" : "Value"}
                        value={drafts[slot.slot_id] || ""}
                        onChange={(e) => setDrafts((prev) => ({ ...prev, [slot.slot_id]: e.target.value }))}
                        placeholder={slot.configured ? "•••• (leave blank unless replacing)" : ""}
                        autoComplete="off"
                      />
                      <Button
                        size="small"
                        variant="contained"
                        disabled={saving === slot.slot_id}
                        onClick={() => void saveSlot(slot.slot_id)}
                      >
                        Save
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        color="inherit"
                        disabled={saving === slot.slot_id || !slot.configured || slot.source === "env"}
                        onClick={() => void clearSlot(slot.slot_id)}
                      >
                        Clear
                      </Button>
                    </Stack>
                  </Stack>
                ))}
              </Stack>
            </CardContent>
          </Card>
        );
      })}
    </Stack>
  );
}

function DemoDataPanel() {
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const demo = useSWR(["crm-demo-seed", CRM_WORKSPACE], () => fetchCrmDemoSeedStatus(CRM_WORKSPACE));

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.location.hash.startsWith("#demo-data")) {
      document.getElementById("demo-data")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [demo.data]);

  const removeDemo = async () => {
    if (!window.confirm("Remove all local CRM demo-seed rows? Real CRM data is left alone.")) {
      return;
    }
    setError(null);
    setMessage(null);
    setBusy(true);
    try {
      let result = await purgeCrmDemoSeed({}, CRM_WORKSPACE);
      if (result.blocked && result.approval?.id) {
        await approveCrmApproval(result.approval.id, CRM_WORKSPACE);
        result = await purgeCrmDemoSeed({ approval_id: result.approval.id }, CRM_WORKSPACE);
      }
      if (result.blocked) {
        setError("Soft Wall approval required. Approve on /crm/ops, then retry Remove demo data.");
        return;
      }
      setMessage(result.hint || "Demo data removed.");
      await demo.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Purge failed");
    } finally {
      setBusy(false);
    }
  };

  const counts = demo.data?.counts || {};
  const present = Boolean(demo.data?.present);
  const countLine = Object.entries(counts)
    .filter(([, n]) => Number(n) > 0)
    .map(([k, n]) => `${k}: ${n}`)
    .join(", ");

  return (
    <Card variant="outlined" id="demo-data">
      <CardContent>
        <Typography variant="subtitle1">Demo data</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Local seed only (tagged demo-seed). Soft Wall gates removal.
        </Typography>
        {error ? (
          <Alert severity="error" sx={{ mt: 1 }}>
            {error}
          </Alert>
        ) : null}
        {message ? (
          <Alert severity="success" sx={{ mt: 1 }}>
            {message}
          </Alert>
        ) : null}
        {demo.error ? (
          <Alert severity="warning" sx={{ mt: 1 }}>
            Could not load demo status.
          </Alert>
        ) : null}
        <Typography variant="body2" sx={{ mt: 1 }}>
          {present ? `Present (${countLine || "rows found"}).` : "No demo-seed rows in this workspace."}
        </Typography>
        <Button
          size="small"
          color="error"
          variant="outlined"
          sx={{ mt: 1.5 }}
          disabled={busy || !present}
          onClick={() => void removeDemo()}
        >
          {busy ? "Removing…" : "Remove demo data"}
        </Button>
      </CardContent>
    </Card>
  );
}

export default function CrmSettingsPage() {
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [cap, setCap] = React.useState("3");
  const summary = useSWR(["crm-settings", CRM_WORKSPACE], () => fetchCrmSettingsSummary(CRM_WORKSPACE));

  const toggleWorkspaceKill = async (enabled: boolean) => {
    setError(null);
    try {
      const result = await upsertCrmKillSwitch(
        { scope: "workspace", enabled, reason: enabled ? "operator pause" : "resume" },
        CRM_WORKSPACE,
      );
      if (result.blocked) {
        setMessage(`Soft Wall required to turn kill switch off: ${result.approval?.id || ""}`);
        return;
      }
      setMessage(enabled ? "Workspace kill switch ON" : "Workspace kill switch OFF");
      await summary.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  };

  const saveCadence = async () => {
    setError(null);
    try {
      await upsertCrmKillSwitch(
        {
          scope: "cadence",
          enabled: true,
          reason: JSON.stringify({ max_emails_per_week: Number(cap) || 3 }),
        },
        CRM_WORKSPACE,
      );
      setMessage("Cadence caps saved (Soft Wall applies when changing live campaigns)");
      await summary.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  };

  const policy = summary.data?.policy as { note?: string; policy_version?: string } | undefined;
  const kills = summary.data?.kill_switches || [];

  return (
    <Stack spacing={2} sx={{ maxWidth: 900 }}>
      <Typography variant="body2" color="text.secondary">
        Kill switches, cadence caps, UK compliance defaults, and Connections (API keys / tokens / flags).
      </Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}
      <DemoDataPanel />
      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1">Workspace kill switch</Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            <Button size="small" color="error" variant="outlined" onClick={() => void toggleWorkspaceKill(true)}>
              Pause outreach
            </Button>
            <Button size="small" variant="outlined" onClick={() => void toggleWorkspaceKill(false)}>
              Resume (Soft Wall)
            </Button>
          </Stack>
          {kills.map((k) => (
            <Typography key={String(k.id)} variant="caption" color="text.secondary" display="block">
              {String(k.scope)} {String(k.scope_id || "")}: {k.enabled ? "ON" : "off"}
            </Typography>
          ))}
        </CardContent>
      </Card>
      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1">Cadence</Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 1 }} alignItems="center">
            <TextField
              size="small"
              label="Max emails / week / contact"
              value={cap}
              onChange={(e) => setCap(e.target.value)}
              sx={{ width: 220 }}
            />
            <Button size="small" variant="contained" onClick={() => void saveCadence()}>
              Save
            </Button>
          </Stack>
        </CardContent>
      </Card>
      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1">UK policy defaults</Typography>
          <Typography variant="body2" color="text.secondary">
            {String(policy?.policy_version || "")}: {String(policy?.note || "")}
          </Typography>
          <Button size="small" component="a" href="/crm/deliverability" sx={{ mt: 1 }}>
            Sender readiness
          </Button>
          <Button size="small" component="a" href="/crm/suppressions" sx={{ ml: 1, mt: 1 }}>
            Suppressions
          </Button>
          <Button size="small" component="a" href="/crm/data-quality" sx={{ ml: 1, mt: 1 }}>
            Data quality
          </Button>
          <Button size="small" component="a" href="/crm/messaging" sx={{ ml: 1, mt: 1 }}>
            Messaging / portals
          </Button>
          <Button size="small" component="a" href="/crm/integrations" sx={{ ml: 1, mt: 1 }}>
            Integrations
          </Button>
          <Button size="small" component="a" href="/crm/attribution" sx={{ ml: 1, mt: 1 }}>
            Attribution
          </Button>
        </CardContent>
      </Card>

      <ConnectionsPanel />
    </Stack>
  );
}
