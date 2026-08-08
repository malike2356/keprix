"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import Grid from "@mui/material/Grid2";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { approveCrmApproval } from "@/lib/crm-api";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

type ProviderRow = {
  name: string;
  status: string;
  budget_remaining?: number;
  description?: string;
};

async function fetchProviders() {
  const res = await ceApi(`/api/crm/enrich/providers`);
  if (!res.ok) throw new Error(parseApiErrorMessage(await res.json().catch(() => ({})), "Providers failed"));
  return res.json() as Promise<{ providers?: ProviderRow[] }>;
}

function statusColor(status: string): "success" | "warning" | "default" | "error" {
  const s = status.toLowerCase();
  if (s === "ready" || s === "ok" || s === "configured") return "success";
  if (s === "not_configured" || s === "disabled") return "warning";
  if (s.includes("error") || s === "failed") return "error";
  return "default";
}

/** Licensed enrichment Soft Wall propose/apply. Sheet enrich lives in the page below. */
export default function CrmLicensedEnrichPanel() {
  const [provider, setProvider] = React.useState("fake_licensed");
  const [leadId, setLeadId] = React.useState("");
  const [runId, setRunId] = React.useState<string | null>(null);
  const [patches, setPatches] = React.useState<unknown[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const data = useSWR(["crm-enrich-providers"], fetchProviders);

  const providers = data.data?.providers || [];
  const known = React.useMemo(() => {
    const names = new Set(providers.map((p) => p.name));
    const fallback = ["fake_licensed", "clearbit_slot"].filter((n) => !names.has(n));
    return [
      ...providers,
      ...fallback.map((name) => ({ name, status: "unknown", budget_remaining: undefined as number | undefined })),
    ];
  }, [providers]);

  const propose = async () => {
    setError(null);
    setMessage(null);
    setBusy(true);
    try {
      const res = await ceApi(`/api/crm/enrich/providers/propose?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider,
          batch: [
            {
              entity_type: "lead",
              entity_id: leadId.trim(),
              fields: { email: null, phone: null },
            },
          ],
        }),
      });
      const payload = await res.json();
      if (!res.ok) throw new Error(parseApiErrorMessage(payload, "Propose failed"));
      if (payload.status === "not_configured") {
        setError(
          `${provider} is not configured. Add a licensed key under CRM Settings, or use fake_licensed for local Soft Wall drills.`,
        );
        return;
      }
      setRunId(String(payload.run_id || ""));
      setPatches(payload.patches || []);
      setMessage(`Proposed ${(payload.patches || []).length} empty-cell patches. Soft Wall apply is still required.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Propose failed");
    } finally {
      setBusy(false);
    }
  };

  const apply = async () => {
    if (!runId) return;
    setError(null);
    setBusy(true);
    try {
      let res = await ceApi(
        `/api/crm/enrich/providers/${encodeURIComponent(runId)}/apply?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" },
      );
      let payload = await res.json();
      if (payload?.blocked && payload?.approval?.id) {
        await approveCrmApproval(payload.approval.id, CRM_WORKSPACE);
        res = await ceApi(
          `/api/crm/enrich/providers/${encodeURIComponent(runId)}/apply?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ approval_id: payload.approval.id }),
          },
        );
        payload = await res.json();
      }
      if (!res.ok) throw new Error(parseApiErrorMessage(payload, "Apply failed"));
      if (payload.blocked) {
        setError("Soft Wall approval required before patches can land.");
        return;
      }
      setMessage(`Applied ${payload.applied ?? 0} · skipped non-empty ${payload.skipped ?? 0}`);
      await data.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Apply failed");
    } finally {
      setBusy(false);
    }
  };

  const reject = async () => {
    if (!runId) return;
    setError(null);
    setBusy(true);
    try {
      const res = await ceApi(
        `/api/crm/enrich/providers/${encodeURIComponent(runId)}/reject?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`,
        { method: "POST" },
      );
      const payload = await res.json();
      if (!res.ok) throw new Error(parseApiErrorMessage(payload, "Reject failed"));
      setMessage("Run rejected. Lead rows were left unchanged.");
      setRunId(null);
      setPatches([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          <Box>
            <Typography variant="h6" component="h2">
              Licensed providers
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Fill empty lead fields from a licensed enrichment slot. Existing values stay untouched.
              Soft Wall gates every apply. Configure keys under{" "}
              <Typography component={Link} href="/crm/settings" color="primary" sx={{ textDecoration: "underline" }}>
                CRM Settings
              </Typography>
              .
            </Typography>
          </Box>

          {error ? (
            <Alert severity="error" onClose={() => setError(null)}>
              {error}
            </Alert>
          ) : null}
          {message ? (
            <Alert severity="success" onClose={() => setMessage(null)}>
              {message}
            </Alert>
          ) : null}
          {data.error ? (
            <Alert severity="warning">Could not load provider health. You can still propose with a known provider id.</Alert>
          ) : null}

          <Grid container spacing={1.5}>
            {known.map((p) => {
              const selected = provider === p.name;
              return (
                <Grid key={p.name} size={{ xs: 12, sm: 6, md: 4 }}>
                  <Card
                    variant="outlined"
                    sx={{
                      height: "100%",
                      cursor: "pointer",
                      borderColor: selected ? "primary.main" : "divider",
                      bgcolor: selected ? "action.selected" : "background.paper",
                      transition: "border-color 120ms ease, background-color 120ms ease",
                      "&:hover": { borderColor: "primary.main" },
                    }}
                    onClick={() => setProvider(p.name)}
                  >
                    <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                      <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
                        <Typography variant="subtitle2">{p.name}</Typography>
                        <Chip size="small" label={p.status} color={statusColor(p.status)} variant="outlined" />
                      </Stack>
                      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.75 }}>
                        Budget remaining: {p.budget_remaining ?? "n/a"}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              );
            })}
          </Grid>

          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "flex-end" }}>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel id="enrich-provider">Provider</InputLabel>
              <Select
                labelId="enrich-provider"
                label="Provider"
                value={provider}
                onChange={(e) => setProvider(String(e.target.value))}
              >
                {known.map((p) => (
                  <MenuItem key={p.name} value={p.name}>
                    {p.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Lead id"
              placeholder="lead_..."
              value={leadId}
              onChange={(e) => setLeadId(e.target.value)}
              sx={{ minWidth: { xs: "100%", md: 280 }, flex: 1 }}
              helperText="Only empty email/phone-style cells are proposed."
            />
            <Button
              variant="outlined"
              disabled={busy || !leadId.trim()}
              onClick={() => void propose()}
            >
              Propose patches
            </Button>
            <Button variant="contained" disabled={busy || !runId} onClick={() => void apply()}>
              Soft Wall apply
            </Button>
            <Button disabled={busy || !runId} onClick={() => void reject()}>
              Reject
            </Button>
          </Stack>

          {runId ? (
            <Typography variant="caption" color="text.secondary">
              Active run: {runId}
            </Typography>
          ) : null}

          {patches.length ? (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Proposed patches ({patches.length})
              </Typography>
              <StructuredDataView value={patches.slice(0, 12)} />
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              Select a provider, enter a lead id, then propose. Review patches here before Soft Wall apply.
            </Typography>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
