"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonTable } from "@/components/ui/loading";
import {
  fetchKernelPlugins,
  fetchKernelTraces,
  type KernelPlugin,
  type KernelPluginFunction,
  type KernelTrace,
} from "@/lib/platform-admin-api";

function asPlugin(row: Record<string, unknown>): KernelPlugin {
  const functions = Array.isArray(row.functions) ? (row.functions as KernelPluginFunction[]) : [];
  return {
    name: String(row.name || row.id || ""),
    version: String(row.version || "-"),
    risk_level: String(row.risk_level || "-"),
    documentation: String(row.documentation || ""),
    capability_tags: Array.isArray(row.capability_tags)
      ? row.capability_tags.map((tag) => String(tag))
      : [],
    auth_requirements: Array.isArray(row.auth_requirements)
      ? row.auth_requirements.map((item) => String(item))
      : [],
    functions,
  };
}

function asTrace(row: Record<string, unknown>): KernelTrace {
  return {
    plugin: String(row.plugin_name || row.plugin || "-"),
    function: String(row.function_name || row.function || row.name || "-"),
    status: String(row.status || "-"),
    duration_ms: typeof row.duration_ms === "number" ? row.duration_ms : null,
    at: String(row.trace_id || row.at || row.timestamp || row.created_at || "-"),
    error: row.error != null ? String(row.error) : null,
  };
}

export default function KernelPluginsPage() {
  const plugins = useSWR("kernel-plugins", fetchKernelPlugins);
  const traces = useSWR("kernel-traces", fetchKernelTraces);
  const [selected, setSelected] = React.useState<string | null>(null);

  const rows = React.useMemo(
    () => (plugins.data?.plugins ?? []).map((row) => asPlugin(row)),
    [plugins.data],
  );
  const traceRows = React.useMemo(
    () => (traces.data?.traces ?? []).map((row) => asTrace(row)),
    [traces.data],
  );

  React.useEffect(() => {
    if (!selected && rows.length > 0) setSelected(rows[0].name);
  }, [rows, selected]);

  const selectedPlugin = rows.find((row) => row.name === selected) || null;

  return (
    <Box>
      <PageHeader
        title="Kernel plugins"
        description="Inspect registered kernel plugins and recent traces."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Kernel" }]}
      />
      {plugins.error ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Kernel API may require API auth: {plugins.error.message}
        </Alert>
      ) : null}

      {plugins.isLoading ? (
        <SkeletonTable rows={4} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No plugins"
          description="Register plugins via /api/kernel/plugins/register."
        />
      ) : (
        <Paper variant="outlined" sx={{ mb: 2, overflow: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Plugin</TableCell>
                <TableCell>Version</TableCell>
                <TableCell>Risk</TableCell>
                <TableCell align="right">Functions</TableCell>
                <TableCell>Tags</TableCell>
                <TableCell>Documentation</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow
                  key={row.name}
                  hover
                  selected={selected === row.name}
                  onClick={() => setSelected(row.name)}
                  sx={{ cursor: "pointer" }}
                >
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                      {row.name}
                    </Typography>
                  </TableCell>
                  <TableCell>{row.version}</TableCell>
                  <TableCell>
                    <Chip size="small" label={row.risk_level} variant="outlined" />
                  </TableCell>
                  <TableCell align="right">{row.functions.length}</TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                      {row.capability_tags.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">
                          -
                        </Typography>
                      ) : (
                        row.capability_tags.map((tag) => (
                          <Chip key={tag} size="small" label={tag} />
                        ))
                      )}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 320 }}>
                      {row.documentation || "-"}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}

      {selectedPlugin ? (
        <Paper variant="outlined" sx={{ p: 2, mb: 2, overflow: "auto" }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Functions in {selectedPlugin.name}
          </Typography>
          {selectedPlugin.functions.length === 0 ? (
            <EmptyState title="No functions" description="This plugin has no registered functions." />
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Function</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell>Invocation</TableCell>
                  <TableCell>Risk</TableCell>
                  <TableCell>Output</TableCell>
                  <TableCell align="right">Cost</TableCell>
                  <TableCell>Permissions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {selectedPlugin.functions.map((fn) => (
                  <TableRow key={fn.name}>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {fn.name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {fn.description || "-"}
                      </Typography>
                    </TableCell>
                    <TableCell>{fn.invocation || "-"}</TableCell>
                    <TableCell>
                      <Chip size="small" label={fn.risk_level || "-"} variant="outlined" />
                    </TableCell>
                    <TableCell>{fn.output_type || "-"}</TableCell>
                    <TableCell align="right">{fn.cost_units ?? "-"}</TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                        {(fn.permissions || []).length === 0 ? (
                          <Typography variant="body2" color="text.secondary">
                            -
                          </Typography>
                        ) : (
                          (fn.permissions || []).map((perm) => (
                            <Chip key={perm} size="small" label={perm} variant="outlined" />
                          ))
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Paper>
      ) : null}

      <Paper variant="outlined" sx={{ p: 2, overflow: "auto" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Traces
        </Typography>
        {traces.error ? (
          <Alert severity="warning">Failed to load traces: {traces.error.message}</Alert>
        ) : traces.isLoading ? (
          <SkeletonTable rows={3} />
        ) : traceRows.length === 0 ? (
          <EmptyState
            title="No traces yet"
            description="Invoke a kernel function to populate recent traces."
          />
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Trace ID</TableCell>
                <TableCell>Plugin</TableCell>
                <TableCell>Function</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Duration (ms)</TableCell>
                <TableCell>Error</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {traceRows.map((row, idx) => (
                <TableRow key={`${row.plugin}-${row.function}-${row.at}-${idx}`}>
                  <TableCell>{row.at}</TableCell>
                  <TableCell>{row.plugin}</TableCell>
                  <TableCell>{row.function}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={row.status}
                      color={row.status === "error" || row.status === "failed" ? "error" : "default"}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="right">{row.duration_ms ?? "-"}</TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {row.error || "-"}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>
    </Box>
  );
}
