"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { CRM_WORKSPACE } from "@/components/crm/types";
import {
  activateCrmIcp,
  approveCrmApproval,
  createCrmIcp,
  diffCrmIcps,
  fetchCrmIcps,
  reviseCrmIcp,
  type CrmIcpDefinition,
} from "@/lib/crm-api";

function parseLines(raw: string): string[] {
  return raw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export default function CrmIcpPage() {
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [name, setName] = React.useState("");
  const [pack, setPack] = React.useState("generic");
  const [includeRaw, setIncludeRaw] = React.useState("");
  const [excludeRaw, setExcludeRaw] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [selected, setSelected] = React.useState<CrmIcpDefinition | null>(null);
  const [diffTarget, setDiffTarget] = React.useState<CrmIcpDefinition | null>(null);
  const [diff, setDiff] = React.useState<Array<{ field: string; from: unknown; to: unknown }> | null>(
    null,
  );

  const data = useSWR(["crm-icp", CRM_WORKSPACE], () => fetchCrmIcps(CRM_WORKSPACE));

  const create = async () => {
    setError(null);
    try {
      await createCrmIcp(
        {
          name: name.trim(),
          pack: pack.trim() || "generic",
          include_rules: parseLines(includeRaw).map((value) => ({ field: "keyword", value })),
          exclude_rules: parseLines(excludeRaw).map((value) => ({ field: "keyword", value })),
          notes: notes.trim() || undefined,
        },
        CRM_WORKSPACE,
      );
      setMessage("ICP v1 created (inactive until Soft Wall activate)");
      setName("");
      setIncludeRaw("");
      setExcludeRaw("");
      setNotes("");
      await data.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  };

  const revise = async (row: CrmIcpDefinition) => {
    setError(null);
    try {
      const next = await reviseCrmIcp(
        row.id,
        {
          exclude_rules: [
            ...(row.exclude_rules || []),
            { field: "keyword", value: `revised-${Date.now().toString(36)}` },
          ],
          notes: `${row.notes || ""} (revised)`.trim(),
        },
        CRM_WORKSPACE,
      );
      setMessage(`Created ${next.icp.name} v${next.icp.version} (inactive)`);
      setSelected(next.icp);
      await data.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Revise failed");
    }
  };

  const activate = async (row: CrmIcpDefinition) => {
    setError(null);
    try {
      let result = await activateCrmIcp(row.id, {}, CRM_WORKSPACE);
      if (result.blocked && result.approval?.id) {
        await approveCrmApproval(result.approval.id, CRM_WORKSPACE);
        result = await activateCrmIcp(row.id, { approval_id: result.approval.id }, CRM_WORKSPACE);
      }
      if (result.blocked) {
        setError("Soft Wall approval required to activate ICP. Approve on /crm then retry.");
        return;
      }
      setMessage(`Activated ${row.name} v${row.version}`);
      await data.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Activate failed");
    }
  };

  const showDiff = async (left: CrmIcpDefinition, right: CrmIcpDefinition) => {
    setError(null);
    try {
      const res = await diffCrmIcps(left.id, right.id, CRM_WORKSPACE);
      setDiff(res.changes || []);
      setDiffTarget(right);
      setSelected(left);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Diff failed");
    }
  };

  const items = data.data?.items || [];
  const active = data.data?.active;

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={1}>
        <BoxTitle />
        <Button size="small" component="a" href="/crm/discover">
          Discover with ICP
        </Button>
      </Stack>

      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}
      {active ? (
        <Alert severity="info">
          Active ICP: {active.name} v{active.version} ({active.pack})
        </Alert>
      ) : (
        <Alert severity="warning">No active ICP. Create a version and Soft Wall activate it.</Alert>
      )}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Create ICP version 1
          </Typography>
          <Stack spacing={1.5}>
            <TextField size="small" label="Name" value={name} onChange={(e) => setName(e.target.value)} />
            <TextField size="small" label="Pack" value={pack} onChange={(e) => setPack(e.target.value)} />
            <TextField
              size="small"
              label="Include keywords (one per line)"
              value={includeRaw}
              onChange={(e) => setIncludeRaw(e.target.value)}
              multiline
              minRows={2}
            />
            <TextField
              size="small"
              label="Exclude keywords (one per line)"
              value={excludeRaw}
              onChange={(e) => setExcludeRaw(e.target.value)}
              multiline
              minRows={2}
            />
            <TextField size="small" label="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
            <Button variant="contained" disabled={!name.trim()} onClick={() => void create()}>
              Create ICP
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Versions
          </Typography>
          {data.isLoading ? (
            <Typography color="text.secondary">Loading ICP definitions...</Typography>
          ) : items.length === 0 ? (
            <Typography color="text.secondary">No ICP definitions yet. No demo ICPs are seeded.</Typography>
          ) : (
            <Stack spacing={1}>
              {items.map((row) => (
                <Stack
                  key={row.id}
                  direction={{ xs: "column", md: "row" }}
                  spacing={1}
                  alignItems={{ md: "center" }}
                  justifyContent="space-between"
                  sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}
                >
                  <Stack spacing={0.25}>
                    <Typography variant="body2">
                      {row.name} v{row.version} {row.active ? "(active)" : ""}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      pack {row.pack} · exclude {(row.exclude_rules || []).length} · include{" "}
                      {(row.include_rules || []).length}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    <Button size="small" onClick={() => setSelected(row)}>
                      Select
                    </Button>
                    <Button size="small" onClick={() => void revise(row)}>
                      Revise
                    </Button>
                    <Button size="small" variant="contained" disabled={Boolean(row.active)} onClick={() => void activate(row)}>
                      Soft Wall activate
                    </Button>
                    {selected && selected.id !== row.id ? (
                      <Button size="small" onClick={() => void showDiff(selected, row)}>
                        Diff vs selected
                      </Button>
                    ) : null}
                  </Stack>
                </Stack>
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>

      {diff && selected && diffTarget ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>
              Diff: {selected.name} v{selected.version} vs v{diffTarget.version}
            </Typography>
            {diff.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No rule changes.
              </Typography>
            ) : (
              <Stack spacing={1}>
                {diff.map((c) => (
                  <Stack key={c.field} spacing={0.5}>
                    <Typography variant="caption" fontWeight={600}>
                      {c.field}
                    </Typography>
                    <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems="flex-start">
                      <Stack spacing={0.25} sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="caption" color="text.secondary">
                          From
                        </Typography>
                        <StructuredDataView value={c.from} />
                      </Stack>
                      <Stack spacing={0.25} sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="caption" color="text.secondary">
                          To
                        </Typography>
                        <StructuredDataView value={c.to} />
                      </Stack>
                    </Stack>
                  </Stack>
                ))}
              </Stack>
            )}
          </CardContent>
        </Card>
      ) : null}
    </Stack>
  );
}

function BoxTitle() {
  return (
    <Stack spacing={0.5}>
      <Typography variant="h5">ICP definitions</Typography>
      <Typography variant="body2" color="text.secondary">
        Immutable versions with Soft Wall activation. Exclusion rules apply before enroll and discovery materialize.
      </Typography>
    </Stack>
  );
}
