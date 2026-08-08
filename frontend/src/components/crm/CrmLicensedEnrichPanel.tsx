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
import StructuredDataView from "@/components/ui/StructuredDataView";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { approveCrmApproval } from "@/lib/crm-api";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

async function fetchProviders() {
  const res = await ceApi(`/api/crm/enrich/providers`);
  if (!res.ok) throw new Error(parseApiErrorMessage(await res.json().catch(() => ({})), "Providers failed"));
  return res.json();
}

/** Licensed enrichment Soft Wall propose/apply (prompt 456). Sheet enrich stays below. */
export default function CrmLicensedEnrichPanel() {
  const [provider, setProvider] = React.useState("fake_licensed");
  const [leadId, setLeadId] = React.useState("");
  const [runId, setRunId] = React.useState<string | null>(null);
  const [patches, setPatches] = React.useState<unknown[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const data = useSWR(["crm-enrich-providers"], fetchProviders);

  const propose = async () => {
    setError(null);
    setMessage(null);
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
        setError(`${provider} is not_configured. Supply a licensed key or use fake_licensed with KEPRIX_FAKE_ENRICH_ALWAYS=1.`);
        return;
      }
      setRunId(String(payload.run_id || ""));
      setPatches(payload.patches || []);
      setMessage(`Proposed ${ (payload.patches || []).length } patches (Soft Wall apply next)`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Propose failed");
    }
  };

  const apply = async () => {
    if (!runId) return;
    setError(null);
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
        setError("Soft Wall approval required");
        return;
      }
      setMessage(`Applied ${payload.applied ?? 0}, skipped non-empty ${payload.skipped ?? 0}`);
      await data.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Apply failed");
    }
  };

  const reject = async () => {
    if (!runId) return;
    setError(null);
    try {
      const res = await ceApi(
        `/api/crm/enrich/providers/${encodeURIComponent(runId)}/reject?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`,
        { method: "POST" },
      );
      const payload = await res.json();
      if (!res.ok) throw new Error(parseApiErrorMessage(payload, "Reject failed"));
      setMessage("Run rejected; rows unchanged");
      setRunId(null);
      setPatches([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reject failed");
    }
  };

  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="subtitle1" gutterBottom>
          Licensed enrichment providers
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Empty cells only, Soft Wall apply, provenance `provider:name`. No default Clearbit scrape. See
          docs/features/crm-licensed-enrichment.md.
        </Typography>
        {error ? <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert> : null}
        {message ? <Alert severity="success" sx={{ mb: 1 }}>{message}</Alert> : null}
        <Stack spacing={1}>
          {(data.data?.providers || []).map(
            (p: { name: string; status: string; budget_remaining?: number }) => (
              <Typography key={p.name} variant="caption" display="block">
                {p.name}: {p.status} · budget left {p.budget_remaining ?? "-"}
              </Typography>
            ),
          )}
          <Stack direction={{ xs: "column", md: "row" }} spacing={1}>
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel id="prov">Provider</InputLabel>
              <Select labelId="prov" label="Provider" value={provider} onChange={(e) => setProvider(e.target.value)}>
                <MenuItem value="fake_licensed">fake_licensed</MenuItem>
                <MenuItem value="clearbit_slot">clearbit_slot</MenuItem>
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Lead id"
              value={leadId}
              onChange={(e) => setLeadId(e.target.value)}
              sx={{ minWidth: 260 }}
            />
            <Button size="small" variant="outlined" disabled={!leadId.trim()} onClick={() => void propose()}>
              Propose
            </Button>
            <Button size="small" variant="contained" disabled={!runId} onClick={() => void apply()}>
              Soft Wall apply
            </Button>
            <Button size="small" disabled={!runId} onClick={() => void reject()}>
              Reject
            </Button>
          </Stack>
          {patches.length ? <StructuredDataView value={patches.slice(0, 8)} /> : null}
        </Stack>
      </CardContent>
    </Card>
  );
}
