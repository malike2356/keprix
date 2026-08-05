"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { SkeletonList } from "@/components/ui/loading";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

type ClientStatus = "pending" | "approved" | "denied" | "revoked" | "expired";

type ClientRecord = {
  fingerprint: string;
  token_id: string;
  status: ClientStatus;
  client_kind: string;
  agent_label: string;
  user_agent_summary: string;
  ip_hash: string;
  requested_scopes: string[];
  workspace_id: string;
  created_at: string;
  updated_at: string;
  last_seen_at: string;
  expires_at?: string | null;
  decided_by?: string | null;
  note?: string | null;
};

type ClientsPayload = {
  clients: ClientRecord[];
  counts: Record<ClientStatus, number>;
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(parseApiErrorMessage(payload, fallback));
  return payload as T;
}

async function fetchClients(status: ClientStatus): Promise<ClientsPayload> {
  return parseJson(
    await ceApi(`/api/security/clients?status=${status}`),
    "Failed to load client approvals",
  );
}

async function decideClient(
  action: "approve" | "deny" | "revoke",
  record: ClientRecord,
): Promise<void> {
  await parseJson(
    await ceApi(`/api/security/clients/${action}`, {
      method: "POST",
      body: JSON.stringify({ fingerprint: record.fingerprint, token_id: record.token_id }),
    }),
    `Failed to ${action} client`,
  );
}

const TABS: ClientStatus[] = ["pending", "approved", "denied", "revoked", "expired"];

export default function ClientApprovalPanel() {
  const [tab, setTab] = React.useState<ClientStatus>("pending");
  const [busyKey, setBusyKey] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const { data, isLoading, mutate } = useSWR(["security-clients", tab], () => fetchClients(tab));

  const onDecide = async (action: "approve" | "deny" | "revoke", record: ClientRecord) => {
    const key = `${action}:${record.fingerprint}`;
    setBusyKey(key);
    setError(null);
    try {
      await decideClient(action, record);
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} client`);
    } finally {
      setBusyKey(null);
    }
  };

  const clients = data?.clients || [];
  const counts = data?.counts;

  return (
    <Box sx={{ py: 2 }}>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Review devices and tools requesting access to your developer API tokens. Approving a client
        allows it to use the associated token for the approval window; deny or revoke to cut it off.
      </Typography>

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}

      <Tabs value={tab} onChange={(_, value: ClientStatus) => setTab(value)} sx={{ mb: 2 }}>
        {TABS.map((status) => (
          <Tab
            key={status}
            value={status}
            label={counts ? `${status} (${counts[status] ?? 0})` : status}
          />
        ))}
      </Tabs>

      {isLoading ? <SkeletonList rows={3} rowHeight={56} /> : null}

      {!isLoading && clients.length === 0 ? (
        <Alert severity="info">No {tab} clients.</Alert>
      ) : null}

      {clients.length > 0 ? (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Client</TableCell>
              <TableCell>Scopes</TableCell>
              <TableCell>Last seen</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {clients.map((record) => (
              <TableRow key={record.fingerprint}>
                <TableCell>
                  <Typography variant="body2">{record.agent_label || record.client_kind}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {record.user_agent_summary || record.fingerprint}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
                    {record.requested_scopes.map((scope) => (
                      <Chip key={scope} size="small" variant="outlined" label={scope} />
                    ))}
                  </Stack>
                </TableCell>
                <TableCell>
                  <Typography variant="caption" color="text.secondary">
                    {record.last_seen_at ? new Date(record.last_seen_at).toLocaleString() : "-"}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    {tab === "pending" ? (
                      <>
                        <Button
                          size="small"
                          variant="contained"
                          disabled={busyKey !== null}
                          onClick={() => void onDecide("approve", record)}
                        >
                          Approve
                        </Button>
                        <Button
                          size="small"
                          color="warning"
                          disabled={busyKey !== null}
                          onClick={() => void onDecide("deny", record)}
                        >
                          Deny
                        </Button>
                      </>
                    ) : null}
                    {tab === "approved" ? (
                      <Button
                        size="small"
                        color="error"
                        disabled={busyKey !== null}
                        onClick={() => void onDecide("revoke", record)}
                      >
                        Revoke
                      </Button>
                    ) : null}
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : null}
    </Box>
  );
}
