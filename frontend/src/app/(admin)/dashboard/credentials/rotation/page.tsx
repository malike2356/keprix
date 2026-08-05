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
import * as React from "react";
import useSWR from "swr";
import PageContainer from "@/components/shared/PageContainer";
import { ceApi } from "@/lib/ce-api";
import { useRequireAdmin } from "@/lib/ce-auth";

type RotationRow = {
  secret_ref: string;
  host: string;
  last_rotated?: string | null;
  cache_ttl: string;
  rotation: { schedule?: string; reminder?: string };
  status: string;
};

type Payload = { credentials: RotationRow[] };

async function fetchRotation(): Promise<Payload> {
  const response = await ceApi("/api/admin/credentials/rotation");
  if (!response.ok) throw new Error("Failed to load rotation status");
  return response.json();
}

function age(value?: string | null): string {
  if (!value) return "Never";
  const ms = Date.now() - new Date(value).getTime();
  const days = Math.floor(ms / 86400000);
  if (days > 0) return `${days}d`;
  const hours = Math.floor(ms / 3600000);
  return `${hours}h`;
}

export default function CredentialRotationPage() {
  useRequireAdmin();
  const { data, error } = useSWR("credential-rotation", fetchRotation);
  return (
    <PageContainer title="Credential rotation" description="Hot reload status, cache TTLs, and rotation reminders." padded={false}>
      <Box sx={{ display: "grid", gap: 2 }}>
        {error ? <Alert severity="error">Failed to load rotation status.</Alert> : null}
        <Paper variant="outlined" sx={{ overflow: "hidden" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Credential</TableCell>
                <TableCell>Host</TableCell>
                <TableCell>Last rotated</TableCell>
                <TableCell>Age</TableCell>
                <TableCell>Next reminder</TableCell>
                <TableCell>Cache TTL</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(data?.credentials || []).map((row) => (
                <TableRow key={`${row.secret_ref}-${row.host}`}>
                  <TableCell>{row.secret_ref}</TableCell>
                  <TableCell>{row.host}</TableCell>
                  <TableCell>{row.last_rotated ? new Date(row.last_rotated).toLocaleString() : "Never"}</TableCell>
                  <TableCell>{age(row.last_rotated)}</TableCell>
                  <TableCell>{row.rotation.reminder || row.rotation.schedule || "-"}</TableCell>
                  <TableCell>{row.cache_ttl}</TableCell>
                  <TableCell><Chip size="small" label={row.status} color={row.status === "healthy" ? "success" : "default"} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      </Box>
    </PageContainer>
  );
}
