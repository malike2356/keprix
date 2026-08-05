"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
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
import { SkeletonList } from "@/components/ui/loading";
import { ceApi } from "@/lib/ce-api";

type UpstreamFeature = {
  feature_id: string;
  name: string;
  description: string;
  category: string;
  version_introduced: string;
  adoption_status: string;
  suggested_status?: string | null;
  security_implications?: string[];
  triage_notes?: string;
  decided_at?: string | null;
  release_url?: string;
  work_package_path?: string | null;
  adoption_prompt_id?: string | null;
};

type UpstreamOverview = {
  report: {
    last_check?: string | null;
    tracked_features?: number;
    pending_review?: number;
    keprix_features?: number;
    inventory_path?: string;
    by_status?: Record<string, number>;
  };
  pending: UpstreamFeature[];
  pending_count: number;
};

const DECISION_OPTIONS = [
  "adopt_with_hardening",
  "adopt",
  "skip",
  "defer",
  "blocked",
  "already_have",
] as const;

async function fetchOverview() {
  const response = await ceApi("/api/admin/upstream");
  if (!response.ok) throw new Error("Could not load upstream queue");
  return (await response.json()) as UpstreamOverview;
}

function statusColor(status: string): "default" | "warning" | "success" | "error" | "info" {
  if (status === "unevaluated") return "warning";
  if (status === "adopt" || status === "adopt_with_hardening") return "info";
  if (status === "already_have") return "success";
  if (status === "blocked") return "error";
  return "default";
}

export default function UpstreamAdoptionPage() {
  const { data, error, isLoading, mutate } = useSWR("admin-upstream", fetchOverview, {
    refreshInterval: 60_000,
  });
  const [busyId, setBusyId] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [runError, setRunError] = React.useState<string | null>(null);
  const [decisions, setDecisions] = React.useState<Record<string, string>>({});

  const runCheck = async () => {
    setBusyId("__check__");
    setRunError(null);
    setMessage(null);
    try {
      const response = await ceApi("/api/admin/upstream/check", { method: "POST" });
      if (!response.ok) throw new Error(await response.text());
      const payload = (await response.json()) as { count: number };
      setMessage(`Upstream check finished (${payload.count} new feature(s)).`);
      await mutate();
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Upstream check failed");
    } finally {
      setBusyId(null);
    }
  };

  const decide = async (featureId: string) => {
    const status = decisions[featureId] || "adopt_with_hardening";
    setBusyId(featureId);
    setRunError(null);
    setMessage(null);
    try {
      const response = await ceApi(`/api/admin/upstream/features/${encodeURIComponent(featureId)}/decide`, {
        method: "POST",
        body: JSON.stringify({ status, decided_by: "admin" }),
      });
      if (!response.ok) throw new Error(await response.text());
      setMessage(`Decided ${featureId}: ${status}`);
      await mutate();
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Decision failed");
    } finally {
      setBusyId(null);
    }
  };

  const adopt = async (featureId: string) => {
    setBusyId(featureId);
    setRunError(null);
    setMessage(null);
    try {
      const response = await ceApi(`/api/admin/upstream/features/${encodeURIComponent(featureId)}/adopt`, {
        method: "POST",
      });
      if (!response.ok) throw new Error(await response.text());
      const payload = (await response.json()) as { prompt_path?: string; work_package_path?: string };
      setMessage(
        `Adoption artifacts generated${payload.prompt_path ? `: ${payload.prompt_path}` : ""}.`,
      );
      await mutate();
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Adopt failed");
    } finally {
      setBusyId(null);
    }
  };

  const pending = data?.pending ?? [];
  const report = data?.report;

  return (
    <Box>
      <PageHeader
        title="Hermes upstream"
        description="Review Hermes releases, approve adoption, and generate Keprix work packages. Automation stops at proposal."
        actions={
          <Button variant="contained" onClick={runCheck} disabled={busyId === "__check__"}>
            {busyId === "__check__" ? "Checking..." : "Run check"}
          </Button>
        }
      />

      {error ? <Alert severity="error">Could not load upstream queue.</Alert> : null}
      {runError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {runError}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }}>
          {message}
        </Alert>
      ) : null}

      {isLoading && !data ? (
        <SkeletonList rows={4} />
      ) : (
        <Stack spacing={2}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} useFlexGap flexWrap="wrap">
              <Typography variant="body2">Pending review: {report?.pending_review ?? pending.length}</Typography>
              <Typography variant="body2">Tracked: {report?.tracked_features ?? 0}</Typography>
              <Typography variant="body2">Keprix capabilities: {report?.keprix_features ?? 0}</Typography>
              <Typography variant="body2">Last check: {report?.last_check || "never"}</Typography>
            </Stack>
          </Paper>

          <Paper variant="outlined">
            <Box sx={{ p: 2, borderBottom: 1, borderColor: "divider" }}>
              <Typography variant="h6">Review queue</Typography>
              <Typography variant="body2" color="text.secondary">
                Approve, skip, or defer before generating adoption prompts.
              </Typography>
            </Box>
            {pending.length === 0 ? (
              <Box sx={{ p: 3 }}>
                <Typography color="text.secondary">No features pending review.</Typography>
              </Box>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Feature</TableCell>
                    <TableCell>Version</TableCell>
                    <TableCell>Suggested</TableCell>
                    <TableCell>Security</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pending.map((feature) => (
                    <TableRow key={feature.feature_id}>
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}>
                          {feature.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" display="block">
                          {feature.feature_id} · {feature.category}
                        </Typography>
                        {feature.triage_notes ? (
                          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                            {feature.triage_notes}
                          </Typography>
                        ) : null}
                      </TableCell>
                      <TableCell>{feature.version_introduced}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={feature.suggested_status || feature.adoption_status}
                          color={statusColor(feature.suggested_status || feature.adoption_status)}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption">
                          {(feature.security_implications || []).length
                            ? `${feature.security_implications!.length} note(s)`
                            : "None"}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={1} justifyContent="flex-end" alignItems="center">
                          <TextField
                            select
                            size="small"
                            label="Decision"
                            value={decisions[feature.feature_id] || feature.suggested_status || "adopt_with_hardening"}
                            onChange={(event) =>
                              setDecisions((prev) => ({
                                ...prev,
                                [feature.feature_id]: event.target.value,
                              }))
                            }
                            sx={{ minWidth: 180 }}
                          >
                            {DECISION_OPTIONS.map((option) => (
                              <MenuItem key={option} value={option}>
                                {option}
                              </MenuItem>
                            ))}
                          </TextField>
                          <Button
                            size="small"
                            variant="outlined"
                            disabled={busyId === feature.feature_id}
                            onClick={() => decide(feature.feature_id)}
                          >
                            Decide
                          </Button>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Paper>

          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              After approval
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Use Adopt on an approved feature (CLI or API) to generate the prompt and work package. Never merge Hermes
              git diffs into Keprix; rebuild against Keprix abstractions, then close with complete.
            </Typography>
            <Stack direction="row" spacing={1}>
              {pending.length === 0 ? (
                <Button
                  size="small"
                  variant="text"
                  onClick={() => {
                    void mutate();
                  }}
                >
                  Refresh
                </Button>
              ) : null}
            </Stack>
            <ApprovedAdoptStrip onAdopt={adopt} busyId={busyId} />
          </Paper>
        </Stack>
      )}
    </Box>
  );
}

function ApprovedAdoptStrip({
  onAdopt,
  busyId,
}: {
  onAdopt: (id: string) => Promise<void>;
  busyId: string | null;
}) {
  const { data } = useSWR("admin-upstream-approved", async () => {
    const response = await ceApi("/api/admin/upstream/features?status=adopt_with_hardening");
    if (!response.ok) return { features: [] as UpstreamFeature[] };
    const harden = (await response.json()) as { features: UpstreamFeature[] };
    const response2 = await ceApi("/api/admin/upstream/features?status=adopt");
    const adopt = response2.ok
      ? ((await response2.json()) as { features: UpstreamFeature[] })
      : { features: [] as UpstreamFeature[] };
    return {
      features: [...harden.features, ...adopt.features].filter(
        (feature) => feature.decided_at && !feature.adoption_prompt_id,
      ),
    };
  });

  const features = data?.features ?? [];
  if (!features.length) {
    return (
      <Typography variant="caption" color="text.secondary">
        No approved features waiting for adopt artifacts.
      </Typography>
    );
  }

  return (
    <Stack spacing={1} sx={{ mt: 1 }}>
      {features.map((feature) => (
        <Stack key={feature.feature_id} direction="row" spacing={1} alignItems="center">
          <Typography variant="body2" sx={{ flex: 1 }}>
            {feature.name}
          </Typography>
          <Button
            size="small"
            variant="contained"
            disabled={busyId === feature.feature_id}
            onClick={() => onAdopt(feature.feature_id)}
          >
            Generate prompt
          </Button>
        </Stack>
      ))}
    </Stack>
  );
}
