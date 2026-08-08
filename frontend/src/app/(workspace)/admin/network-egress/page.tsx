"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList, SkeletonTable } from "@/components/ui/loading";
import { useCESession } from "@/lib/ce-auth";
import {
  type EgressDecision,
  fetchEgressAudit,
  fetchEgressPolicies,
} from "@/lib/network-egress-api";

function isAdminRole(role: string | undefined): boolean {
  const r = (role || "").toLowerCase();
  return r === "admin" || r === "owner" || r === "superadmin" || r === "developer";
}

function formatTs(ts?: number): string {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

export default function AdminNetworkEgressPage() {
  const { user, isLoading: sessionLoading } = useCESession();
  const isAdmin = isAdminRole(user?.role);
  const [tab, setTab] = React.useState(0);
  const [productId, setProductId] = React.useState("");
  const [decision, setDecision] = React.useState<EgressDecision | "">("");
  const [hostFilter, setHostFilter] = React.useState("");
  const [limit, setLimit] = React.useState(100);

  const auditKey = isAdmin
    ? ["network-egress-audit", productId, decision, limit]
    : null;
  const audit = useSWR(auditKey, () =>
    fetchEgressAudit({
      n: limit,
      productId: productId.trim() || undefined,
      decision: decision || undefined,
    }),
  );
  const policies = useSWR(isAdmin ? "network-egress-policy" : null, fetchEgressPolicies);

  const entries = React.useMemo(() => {
    const rows = audit.data?.entries ?? [];
    const host = hostFilter.trim().toLowerCase();
    if (!host) return rows;
    return rows.filter((row) => {
      const hay = `${row.host || ""} ${row.url_path || ""} ${row.tool_name || ""}`.toLowerCase();
      return hay.includes(host);
    });
  }, [audit.data, hostFilter]);

  if (sessionLoading) {
    return (
      <Box>
        <PageHeader title="Network egress" description="Outbound network policy and audit." />
        <SkeletonList rows={4} rowHeight={48} />
      </Box>
    );
  }

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader
          title="Network egress"
          description="Outbound network policy and allowlists for agent tool calls."
          breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Network egress" }]}
        />
        <Alert severity="error">Admin role required to view egress audit and policy.</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title="Network egress"
        description="Outbound network decisions for agent tool calls. Allowlists are loaded from product policy manifests; this page is the live audit and policy snapshot."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Network egress" }]}
        actions={
          <Button component={NextLink} href="/admin/tool-acl" size="small" variant="outlined">
            Tool ACL
          </Button>
        }
      />

      <Alert severity="info" sx={{ mb: 2 }}>
        Enforcement is active on the backend. Editing allowlists happens in product egress policy /
        manifests, not as free-form admin URLs from this page.
      </Alert>

      {(audit.error || policies.error) && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {audit.error?.message || policies.error?.message || "Failed to load egress data"}
        </Alert>
      )}

      <Tabs value={tab} onChange={(_, v: number) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Audit log" />
        <Tab label="Policies" />
      </Tabs>

      {tab === 0 ? (
        <Stack spacing={2}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "center" }}>
            <TextField
              size="small"
              label="Product id"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              placeholder="e.g. aiva"
            />
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel id="egress-decision">Decision</InputLabel>
              <Select
                labelId="egress-decision"
                label="Decision"
                value={decision}
                onChange={(e) => setDecision(e.target.value as EgressDecision | "")}
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="ALLOWED">ALLOWED</MenuItem>
                <MenuItem value="BLOCKED">BLOCKED</MenuItem>
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Host / tool filter"
              value={hostFilter}
              onChange={(e) => setHostFilter(e.target.value)}
            />
            <FormControl size="small" sx={{ minWidth: 100 }}>
              <InputLabel id="egress-limit">Limit</InputLabel>
              <Select
                labelId="egress-limit"
                label="Limit"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
              >
                {[50, 100, 200, 500].map((n) => (
                  <MenuItem key={n} value={n}>
                    {n}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button onClick={() => void audit.mutate()}>Refresh</Button>
          </Stack>

          {audit.isLoading ? (
            <SkeletonTable rows={8} columns={7} />
          ) : entries.length === 0 ? (
            <EmptyState
              title="No egress events"
              description="When tools make outbound HTTP calls, ALLOWED and BLOCKED decisions appear here for today."
            />
          ) : (
            <Paper variant="outlined" sx={{ overflow: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Time</TableCell>
                    <TableCell>Product</TableCell>
                    <TableCell>Host</TableCell>
                    <TableCell>IP</TableCell>
                    <TableCell>Decision</TableCell>
                    <TableCell>Reason</TableCell>
                    <TableCell>Tool</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {[...entries].reverse().map((row, idx) => (
                    <TableRow key={`${row.ts}-${row.host}-${idx}`} hover>
                      <TableCell>{formatTs(row.ts)}</TableCell>
                      <TableCell>{row.product_id || "—"}</TableCell>
                      <TableCell>
                        <Typography variant="body2">{row.host || "—"}</Typography>
                        {row.url_path ? (
                          <Typography variant="caption" color="text.secondary" display="block">
                            {row.url_path}
                          </Typography>
                        ) : null}
                      </TableCell>
                      <TableCell>{row.ip || "—"}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={row.decision || "—"}
                          color={row.decision === "BLOCKED" ? "error" : "success"}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>{row.reason || "—"}</TableCell>
                      <TableCell>{row.tool_name || "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>
          )}
        </Stack>
      ) : null}

      {tab === 1 ? (
        policies.isLoading ? (
          <SkeletonList rows={3} rowHeight={80} />
        ) : (policies.data?.products ?? []).length === 0 ? (
          <EmptyState
            title="No product egress policies registered"
            description="Products register allowed_hosts when their policy manifests load. Until then the gate still blocks private/metadata destinations."
          />
        ) : (
          <Stack spacing={2}>
            {(policies.data?.products || []).map((product) => {
              const policy = policies.data?.policies?.[product] || {};
              return (
                <Paper key={product} variant="outlined" sx={{ p: 2 }}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                    <Typography variant="h6" component="h2">
                      {product}
                    </Typography>
                    <Chip
                      size="small"
                      label={policy.default_deny ? "default deny" : "default allow"}
                      color={policy.default_deny ? "warning" : "default"}
                      variant="outlined"
                    />
                  </Stack>
                  <Typography variant="subtitle2" sx={{ mt: 1 }}>
                    Allowed hosts
                  </Typography>
                  <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
                    {(policy.allowed_hosts || []).length === 0 ? (
                      <Typography variant="body2" color="text.secondary">
                        (none)
                      </Typography>
                    ) : (
                      (policy.allowed_hosts || []).map((host) => (
                        <Chip key={host} size="small" label={host} />
                      ))
                    )}
                  </Stack>
                  <Typography variant="subtitle2">Extra denied hosts</Typography>
                  <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
                    {(policy.extra_denied_hosts || []).length === 0 ? (
                      <Typography variant="body2" color="text.secondary">
                        (none)
                      </Typography>
                    ) : (
                      (policy.extra_denied_hosts || []).map((host) => (
                        <Chip key={host} size="small" color="error" variant="outlined" label={host} />
                      ))
                    )}
                  </Stack>
                </Paper>
              );
            })}
          </Stack>
        )
      ) : null}
    </Box>
  );
}
