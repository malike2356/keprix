"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageContainer from "@/components/shared/PageContainer";
import { ceApi } from "@/lib/ce-api";
import { useRequireAdmin } from "@/lib/ce-auth";
import ProxyOpsPanel from "@/components/admin/ProxyOpsPanel";

type CredentialAudit = {
  id: string;
  timestamp: string;
  tool: string;
  route: { host: string; path?: string; method?: string };
  credential_ref: string;
  status: string;
  duration_ms?: number | null;
  response_status?: number | null;
  rotation_docs_url?: string | null;
};

type Payload = {
  audit: CredentialAudit[];
  validation: { ok: boolean; fail_count: number; warn_count: number; total: number };
};

async function fetchCredentials(): Promise<Payload> {
  const response = await ceApi("/api/admin/credentials");
  if (!response.ok) throw new Error("Failed to load credential audit trail");
  return response.json();
}

export default function AdminCredentialsPage() {
  useRequireAdmin();
  const { data, error } = useSWR("admin-credentials", fetchCredentials);

  return (
    <PageContainer title="Credential isolation" description="Tool credential routes, proxy validation, and external API audit trail." padded={false}>
      <Box sx={{ display: "grid", gap: 2 }}>
        <ProxyOpsPanel />
        {error ? <Alert severity="error">Failed to load credential audit trail.</Alert> : null}
        <Paper variant="outlined" sx={{ p: 2, display: "flex", gap: 1, flexWrap: "wrap", alignItems: "center" }}>
          <Typography variant="subtitle2">Startup validation</Typography>
          <Chip color={data?.validation.ok ? "success" : "error"} label={data?.validation.ok ? "OK" : "Blocked"} />
          <Chip variant="outlined" label={`${data?.validation.total ?? 0} routes`} />
          <Chip variant="outlined" color="warning" label={`${data?.validation.warn_count ?? 0} warnings`} />
          <Chip variant="outlined" color="error" label={`${data?.validation.fail_count ?? 0} failures`} />
        </Paper>
        <Paper variant="outlined" sx={{ overflow: "hidden" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Timestamp</TableCell>
                <TableCell>Tool</TableCell>
                <TableCell>Route</TableCell>
                <TableCell>Credential</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Duration</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(data?.audit || []).map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{new Date(row.timestamp).toLocaleString()}</TableCell>
                  <TableCell>{row.tool}</TableCell>
                  <TableCell>{[row.route.method, row.route.host, row.route.path].filter(Boolean).join(" ")}</TableCell>
                  <TableCell>{row.credential_ref}</TableCell>
                  <TableCell>
                    <Chip size="small" color={row.response_status === 401 ? "warning" : "default"} label={row.response_status ? `${row.response_status} ${row.status}` : row.status} />
                  </TableCell>
                  <TableCell align="right">{row.duration_ms == null ? "-" : `${Math.round(row.duration_ms)}ms`}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      </Box>
    </PageContainer>
  );
}
