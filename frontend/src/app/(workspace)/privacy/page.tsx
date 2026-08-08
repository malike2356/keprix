"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { ceApi } from "@/lib/ce-api";

async function fetchConsents() {
  const response = await ceApi("/api/privacy/consent");
  if (!response.ok) throw new Error("Failed to load consents");
  return response.json();
}

async function fetchDsar() {
  const response = await ceApi("/api/privacy/dsar");
  if (!response.ok) throw new Error("Failed to load DSAR requests");
  return response.json();
}

async function fetchHealth() {
  const response = await ceApi("/api/privacy/health");
  if (!response.ok) throw new Error("Failed to load privacy health");
  return response.json();
}

async function fetchRetention() {
  const response = await ceApi("/api/privacy/retention");
  if (!response.ok) throw new Error("Failed to load retention policies");
  return response.json();
}

type RetentionPolicy = {
  data_category: string;
  retain_days: number;
  action: string;
};

export default function PrivacyPage() {
  const { data: consents, mutate: mutateConsents } = useSWR("privacy-consents", fetchConsents);
  const { data: dsar, mutate: mutateDsar } = useSWR("privacy-dsar", fetchDsar);
  const { data: health, mutate: mutateHealth } = useSWR("privacy-health", fetchHealth);
  const { data: retention, mutate: mutateRetention } = useSWR("privacy-retention", fetchRetention);
  const [purpose, setPurpose] = React.useState("analytics");
  const [granted, setGranted] = React.useState(true);
  const [eraseConfirm, setEraseConfirm] = React.useState(false);
  const [dryRunResult, setDryRunResult] = React.useState<unknown | null>(null);
  const [policyEdits, setPolicyEdits] = React.useState<Record<string, RetentionPolicy>>({});

  React.useEffect(() => {
    if (!retention?.policies) return;
    const next: Record<string, RetentionPolicy> = {};
    for (const policy of retention.policies as RetentionPolicy[]) {
      next[policy.data_category] = policy;
    }
    setPolicyEdits(next);
  }, [retention]);

  const recordConsent = async () => {
    await ceApi("/api/privacy/consent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ purpose, granted }),
    });
    await mutateConsents();
  };

  const requestDsar = async () => {
    await ceApi("/api/privacy/dsar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_type: "access" }),
    });
    await mutateDsar();
  };

  const eraseData = async (dryRun: boolean) => {
    const response = await ceApi("/api/privacy/erase", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope: "full", confirm: dryRun ? false : eraseConfirm, dry_run: dryRun }),
    });
    const payload = await response.json();
    if (dryRun) {
      setDryRunResult(payload.would_remove || payload);
      return;
    }
    setEraseConfirm(false);
    setDryRunResult(null);
    await mutateHealth();
  };

  const saveRetention = async (policy: RetentionPolicy) => {
    await ceApi(`/api/privacy/retention/${policy.data_category}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        retain_days: policy.retain_days,
        action: policy.action,
      }),
    });
    await mutateRetention();
    await mutateHealth();
  };

  const runRetention = async () => {
    await ceApi("/api/privacy/retention/run", { method: "POST" });
    await mutateRetention();
    await mutateHealth();
  };

  return (
    <Box>
      <PageHeader title="Privacy" description="Consent, data access requests, retention, and erasure." />
      <Box sx={{ display: "grid", gap: 2, maxWidth: 900 }}>
        {health ? (
          <Alert severity="info">
            GDPR health: {health.pending_dsars} pending DSARs. Last retention run:{" "}
            {health.last_retention_run || "never"}.
          </Alert>
        ) : null}

        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Data retention
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Category</TableCell>
                  <TableCell>Retain days</TableCell>
                  <TableCell>Action</TableCell>
                  <TableCell align="right">Save</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {Object.values(policyEdits).map((policy) => (
                  <TableRow key={policy.data_category}>
                    <TableCell>{policy.data_category}</TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        type="number"
                        value={policy.retain_days}
                        onChange={(event) =>
                          setPolicyEdits((prev) => ({
                            ...prev,
                            [policy.data_category]: {
                              ...policy,
                              retain_days: Number(event.target.value),
                            },
                          }))
                        }
                        sx={{ width: 110 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        select
                        value={policy.action}
                        onChange={(event) =>
                          setPolicyEdits((prev) => ({
                            ...prev,
                            [policy.data_category]: {
                              ...policy,
                              action: event.target.value,
                            },
                          }))
                        }
                        sx={{ minWidth: 130 }}
                      >
                        <MenuItem value="anonymise">anonymise</MenuItem>
                        <MenuItem value="delete">delete</MenuItem>
                      </TextField>
                    </TableCell>
                    <TableCell align="right">
                      <Button size="small" onClick={() => void saveRetention(policy)}>
                        Save
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Button sx={{ mt: 2 }} variant="outlined" onClick={() => void runRetention()}>
              Run retention now
            </Button>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Consent
            </Typography>
            <TextField
              label="Purpose"
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              size="small"
              fullWidth
              sx={{ mb: 2 }}
            />
            <FormControlLabel
              control={<Checkbox checked={granted} onChange={(e) => setGranted(e.target.checked)} />}
              label="Granted"
            />
            <Box sx={{ mt: 2 }}>
              <Button variant="contained" onClick={() => void recordConsent()}>
                Save consent
              </Button>
            </Box>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>
              {(consents?.consents ?? []).length} records on file
            </Typography>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Data access (DSAR)
            </Typography>
            <Button variant="outlined" onClick={() => void requestDsar()}>
              Request export
            </Button>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>
              {(dsar?.requests ?? []).length} requests
            </Typography>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Erasure
            </Typography>
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
              <Button variant="outlined" onClick={() => void eraseData(true)}>
                Dry run
              </Button>
              <FormControlLabel
                control={<Checkbox checked={eraseConfirm} onChange={(e) => setEraseConfirm(e.target.checked)} />}
                label="I confirm I want to erase my workspace data"
              />
              <Button variant="contained" color="error" disabled={!eraseConfirm} onClick={() => void eraseData(false)}>
                Erase my data
              </Button>
            </Box>
            {dryRunResult ? <StructuredDataView value={dryRunResult} /> : null}
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}
