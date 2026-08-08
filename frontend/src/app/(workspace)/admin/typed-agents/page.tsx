"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
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
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { SkeletonTable } from "@/components/ui/loading";
import {
  fetchTypedAgentSchemas,
  fetchTypedAgents,
  runTypedAgent,
  type TypedAgentInventoryRow,
} from "@/lib/platform-admin-api";

function samplePayloadFor(name: string, tools: string[]) {
  if (name === "support-agent" || tools.includes("lookup_ticket")) {
    return {
      workspace_id: "default",
      tool_calls: [{ name: "lookup_ticket", arguments: { ticket_id: "TCK-1001" } }],
      raw_output: {
        ticket_id: "TCK-1001",
        resolution: "Reset MFA and confirm recovery codes",
        cited_policy: "AUTH-MFA-01",
      },
    };
  }
  const first = tools[0] || "noop";
  return {
    workspace_id: "default",
    tool_calls: first ? [{ name: first, arguments: {} }] : [],
    raw_output: {},
  };
}

function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function TypedAgentsPage() {
  const agents = useSWR("typed-agents", fetchTypedAgents);
  const [name, setName] = React.useState<string | null>(null);
  const [workspaceId, setWorkspaceId] = React.useState("default");
  const [confirm, setConfirm] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [runResult, setRunResult] = React.useState<unknown>(null);

  const schemas = useSWR(name ? ["typed-agent-schemas", name] : null, () => fetchTypedAgentSchemas(name!));

  const inventory: TypedAgentInventoryRow[] = React.useMemo(() => {
    if (agents.data?.inventory?.length) return agents.data.inventory;
    return (agents.data?.agents ?? []).map((agentName) => ({
      name: agentName,
      tool_count: 0,
      tools: [],
      approval_gated_tools: 0,
      output_schema: "-",
      deps_schema: "-",
    }));
  }, [agents.data]);

  React.useEffect(() => {
    if (!name && inventory.length > 0) setName(inventory[0].name);
  }, [inventory, name]);

  const selected = inventory.find((row) => row.name === name) || null;
  const schemaTools = schemas.data?.tools ?? [];
  const toolNames = schemaTools.map((tool) => tool.name).filter(Boolean) as string[];

  async function runSample(autoApprove: boolean) {
    if (!name) return;
    setBusy(true);
    setError(null);
    try {
      const sample = samplePayloadFor(name, toolNames.length ? toolNames : selected?.tools || []);
      const result = await runTypedAgent(name, {
        ...sample,
        workspace_id: workspaceId || "default",
        auto_approve: autoApprove,
      });
      setRunResult(result);
      setConfirm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sample run failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box>
      <PageHeader
        title="Typed agents"
        description="Operator inventory of registered typed agents: schemas, tools, Soft Wall sample runs, and JSON export."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Typed agents" }]}
      />

      {(agents.error || error) && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error || (agents.error instanceof Error ? agents.error.message : "Failed to load")}
        </Alert>
      )}

      {agents.isLoading ? (
        <SkeletonTable rows={4} />
      ) : inventory.length === 0 ? (
        <EmptyState title="No typed agents" description="Registry is empty in this runtime. Bootstrap registers support-agent by default." />
      ) : (
        <Paper variant="outlined" sx={{ mb: 2, overflow: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Output</TableCell>
                <TableCell>Dependencies</TableCell>
                <TableCell align="right">Tools</TableCell>
                <TableCell align="right">Approval-gated</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {inventory.map((row) => (
                <TableRow
                  key={row.name}
                  hover
                  selected={name === row.name}
                  onClick={() => {
                    setName(row.name);
                    setRunResult(null);
                    setError(null);
                  }}
                  sx={{ cursor: "pointer" }}
                >
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                      {row.name}
                    </Typography>
                  </TableCell>
                  <TableCell>{row.output_schema}</TableCell>
                  <TableCell>{row.deps_schema}</TableCell>
                  <TableCell align="right">{row.tool_count}</TableCell>
                  <TableCell align="right">{row.approval_gated_tools}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}

      {name ? (
        <Stack spacing={2}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }} justifyContent="space-between">
              <Box>
                <Typography variant="h6">{name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  Schema export and Soft Wall sample run for /api/typed-agents/{name}
                </Typography>
              </Box>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                <Button
                  variant="outlined"
                  disabled={!schemas.data || schemas.isLoading}
                  onClick={() => downloadJson(`${name}-schemas.json`, schemas.data || {})}
                >
                  Export schema JSON
                </Button>
                <Button disabled={busy || schemas.isLoading} onClick={() => void runSample(false)}>
                  Dry run sample
                </Button>
                <Button color="warning" disabled={busy || schemas.isLoading} onClick={() => setConfirm(true)}>
                  Soft Wall run
                </Button>
              </Stack>
            </Stack>

            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mt: 2 }}>
              <TextField
                size="small"
                label="Workspace id"
                value={workspaceId}
                onChange={(e) => setWorkspaceId(e.target.value)}
                sx={{ maxWidth: 280 }}
              />
              <Chip size="small" label={`${schemaTools.length || selected?.tool_count || 0} tools`} />
              <Chip
                size="small"
                color={(selected?.approval_gated_tools || 0) > 0 ? "warning" : "default"}
                label={`${selected?.approval_gated_tools ?? 0} approval-gated`}
              />
            </Stack>
          </Paper>

          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Tools
            </Typography>
            {schemas.isLoading ? (
              <Typography variant="body2" color="text.secondary">
                Loading schemas...
              </Typography>
            ) : schemaTools.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No tools exported for this agent.
              </Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Tool</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Approval</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {schemaTools.map((tool) => (
                    <TableRow key={tool.name}>
                      <TableCell>{tool.name}</TableCell>
                      <TableCell>{tool.description || "-"}</TableCell>
                      <TableCell>{tool.approval_action || "none"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Paper>

          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Schemas
            </Typography>
            <Stack spacing={1.5}>
              {(
                [
                  ["Output", schemas.data?.output_schema],
                  ["Dependencies", schemas.data?.dependencies_schema],
                  ["Context", schemas.data?.context_schema],
                ] as Array<[string, Record<string, unknown> | undefined]>
              ).map(([label, schema]) => (
                <Box key={label}>
                  <Typography variant="subtitle2">{label}</Typography>
                  <StructuredDataView value={schema || {}} />
                </Box>
              ))}
            </Stack>
          </Paper>

          {runResult ? (
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="subtitle1" sx={{ mb: 1 }}>
                Last sample run
              </Typography>
              <StructuredDataView value={runResult} />
            </Paper>
          ) : null}
        </Stack>
      ) : null}

      <Dialog open={confirm} onClose={() => setConfirm(false)}>
        <DialogTitle>Soft Wall sample run?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Confirm Soft Wall run for {name} with auto_approve=true. This exercises tool and output publication
            approvals for the sample payload in workspace {workspaceId || "default"}.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirm(false)}>Cancel</Button>
          <Button color="warning" variant="contained" disabled={busy} onClick={() => void runSample(true)}>
            Confirm Soft Wall run
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
