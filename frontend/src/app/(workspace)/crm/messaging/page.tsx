"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { approveCrmApproval } from "@/lib/crm-api";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

async function fetchMessaging() {
  const res = await ceApi(`/api/crm/messaging/status?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`);
  if (!res.ok) throw new Error(parseApiErrorMessage(await res.json().catch(() => ({})), "Messaging failed"));
  return res.json();
}

async function fetchPortals() {
  const res = await ceApi(`/api/crm/property-portals/status?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`);
  if (!res.ok) throw new Error(parseApiErrorMessage(await res.json().catch(() => ({})), "Portals failed"));
  return res.json();
}

async function fetchSocial() {
  const res = await ceApi(`/api/crm/social/health`);
  if (!res.ok) throw new Error(parseApiErrorMessage(await res.json().catch(() => ({})), "Social failed"));
  return res.json();
}

export default function CrmMessagingPage() {
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [tplName, setTplName] = React.useState("welcome");
  const [tplBody, setTplBody] = React.useState("Hello from Keprix");
  const [tplChannel, setTplChannel] = React.useState("sms");
  const [ackNotes, setAckNotes] = React.useState("Operator acknowledged checklist");

  const messaging = useSWR(["crm-msg", CRM_WORKSPACE], fetchMessaging);
  const portals = useSWR(["crm-portals", CRM_WORKSPACE], fetchPortals);
  const social = useSWR(["crm-social"], fetchSocial);

  const softWallRetry = async (
    first: () => Promise<Response>,
    retry: (approvalId: string) => Promise<Response>,
  ) => {
    let res = await first();
    let payload = await res.json();
    if (payload?.blocked && payload?.approval?.id) {
      await approveCrmApproval(payload.approval.id, CRM_WORKSPACE);
      res = await retry(payload.approval.id);
      payload = await res.json();
    }
    return { res, payload };
  };

  const enableChannels = async (enabled: boolean) => {
    setError(null);
    try {
      const { res, payload } = await softWallRetry(
        () =>
          ceApi(`/api/crm/messaging/enable?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled }),
          }),
        (approvalId) =>
          ceApi(`/api/crm/messaging/enable?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled, approval_id: approvalId }),
          }),
      );
      if (!res.ok || payload.blocked || payload.error) {
        setError(String(payload.message || payload.error || "Enable failed (flag may be off)"));
        return;
      }
      setMessage(enabled ? "Workspace WhatsApp/SMS enabled" : "Workspace WhatsApp/SMS disabled");
      await messaging.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Enable failed");
    }
  };

  const registerTemplate = async () => {
    setError(null);
    try {
      const { res, payload } = await softWallRetry(
        () =>
          ceApi(`/api/crm/messaging/templates?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ channel: tplChannel, name: tplName, body: tplBody }),
          }),
        (approvalId) =>
          ceApi(`/api/crm/messaging/templates?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              channel: tplChannel,
              name: tplName,
              body: tplBody,
              approval_id: approvalId,
            }),
          }),
      );
      if (!res.ok || payload.blocked) {
        setError("Soft Wall required for template approval");
        return;
      }
      setMessage(`Template ${tplName} approved`);
      await messaging.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Template failed");
    }
  };

  const ackPortals = async () => {
    setError(null);
    try {
      const { res, payload } = await softWallRetry(
        () =>
          ceApi(`/api/crm/property-portals/acknowledge?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notes: ackNotes }),
          }),
        (approvalId) =>
          ceApi(`/api/crm/property-portals/acknowledge?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notes: ackNotes, approval_id: approvalId }),
          }),
      );
      if (!res.ok || payload.blocked) {
        setError("Soft Wall required for portal checklist");
        return;
      }
      setMessage("Property portal checklist acknowledged");
      await portals.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ack failed");
    }
  };

  const setKill = async (engaged: boolean) => {
    setError(null);
    try {
      const res = await ceApi(`/api/crm/property-portals/kill-switch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ engaged }),
      });
      const payload = await res.json();
      if (!res.ok) throw new Error(parseApiErrorMessage(payload, "Kill switch failed"));
      setMessage(engaged ? "Portal kill switch ON" : "Portal kill switch OFF");
      await portals.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kill switch failed");
    }
  };

  const provider = messaging.data?.provider || {};
  const settings = messaging.data?.settings || {};
  const templates = messaging.data?.templates || [];

  return (
    <Stack spacing={2} sx={{ maxWidth: 960 }}>
      <Typography variant="h5">Channels and gated sources</Typography>
      <Typography variant="body2" color="text.secondary">
        WhatsApp/SMS (flag off by default), social API health (scrape refused), and property portal checklist gates.
        Enter tokens and channel flags under{" "}
        <Typography component="a" href="/crm/settings#connections" color="primary" sx={{ textDecoration: "underline" }}>
          /crm/settings Connections
        </Typography>
        . Soft Wall still applies before enable/ack/template/first send.
      </Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            WhatsApp / SMS
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Flag {String(provider.feature_flag)}: {provider.flag_enabled ? "on" : "off"} · workspace toggle:{" "}
            {settings.whatsapp_sms_enabled ? "on" : "off"} · WA {provider.whatsapp?.status} · SMS{" "}
            {provider.sms?.status}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap>
            <Button size="small" variant="contained" onClick={() => void enableChannels(true)}>
              Soft Wall enable workspace
            </Button>
            <Button size="small" onClick={() => void enableChannels(false)}>
              Disable workspace
            </Button>
            <Button size="small" component="a" href="/crm/contactability">
              Consent / contactability
            </Button>
          </Stack>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ mt: 2 }}>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel id="tpl-ch">Channel</InputLabel>
              <Select
                labelId="tpl-ch"
                label="Channel"
                value={tplChannel}
                onChange={(e) => setTplChannel(e.target.value)}
              >
                <MenuItem value="sms">sms</MenuItem>
                <MenuItem value="whatsapp">whatsapp</MenuItem>
              </Select>
            </FormControl>
            <TextField size="small" label="Template name" value={tplName} onChange={(e) => setTplName(e.target.value)} />
            <TextField size="small" label="Body" value={tplBody} onChange={(e) => setTplBody(e.target.value)} sx={{ flex: 1 }} />
            <Button size="small" variant="outlined" onClick={() => void registerTemplate()}>
              Soft Wall approve template
            </Button>
          </Stack>
          <Typography variant="caption" display="block" sx={{ mt: 1 }}>
            Templates: {templates.length}. Unapproved templates cannot send.
          </Typography>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Social APIs (LinkedIn / Meta / TikTok)
          </Typography>
          {(social.data?.adapters || []).map(
            (a: { name?: string; status?: string; message?: string; required_scopes?: string[] }) => (
              <Typography key={String(a.name)} variant="body2">
                {a.name}: {a.status}
                {a.message ? ` (${a.message})` : ""}
                {a.required_scopes?.length ? ` · scopes: ${a.required_scopes.join(", ")}` : ""}
              </Typography>
            ),
          )}
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            {social.data?.scrape?.message || "Scrape adapters remain refused."} Use Discover with official API adapters
            or CSV when configured.
          </Typography>
          <Button size="small" component="a" href="/crm/discover" sx={{ mt: 1 }}>
            Open Discover
          </Button>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Property portals
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Flag enabled: {String(portals.data?.flag_enabled)} · checklist ack:{" "}
            {portals.data?.acknowledged ? "yes" : "no"} · kill switch: {String(portals.data?.kill_switch)}
          </Typography>
          <TextField
            size="small"
            fullWidth
            label="Ack notes"
            value={ackNotes}
            onChange={(e) => setAckNotes(e.target.value)}
            sx={{ mt: 1 }}
          />
          <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap>
            <Button size="small" variant="contained" onClick={() => void ackPortals()}>
              Soft Wall acknowledge checklist
            </Button>
            <Button size="small" color="warning" onClick={() => void setKill(true)}>
              Engage kill switch
            </Button>
            <Button size="small" onClick={() => void setKill(false)}>
              Clear kill switch
            </Button>
          </Stack>
          <Typography variant="caption" display="block" sx={{ mt: 1 }}>
            HTML scrape stays refused. Licensed feed path needs env + checklist. Docs: property-portal legal checklist.
          </Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
