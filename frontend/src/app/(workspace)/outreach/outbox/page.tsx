"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
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
import { cancelCrmOutbox, fetchCrmOutbox, retryCrmOutbox } from "@/lib/crm-api";

const WORKSPACE = "default";

export default function OutreachOutboxPage() {
  const [status, setStatus] = React.useState("");
  const { data, error, mutate, isLoading } = useSWR(["crm-outbox", WORKSPACE, status], () =>
    fetchCrmOutbox(WORKSPACE, status || undefined),
  );
  const [busyId, setBusyId] = React.useState<string | null>(null);
  const [msg, setMsg] = React.useState<string | null>(null);
  const [err, setErr] = React.useState<string | null>(null);

  const act = async (id: string, action: "retry" | "cancel") => {
    setBusyId(id);
    setErr(null);
    try {
      if (action === "retry") {
        const result = await retryCrmOutbox(id, {}, WORKSPACE);
        if (result.blocked) {
          setMsg(`Soft Wall approval required for retry. See Approvals.`);
        } else {
          setMsg(`Re-queued with idempotency key ${result.idempotency_key || "(same key)"}`);
        }
      } else {
        await cancelCrmOutbox(id, WORKSPACE);
        setMsg("Cancelled");
      }
      await mutate();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  };

  const items = data?.items ?? [];

  return (
    <Stack spacing={2}>
      {error || err ? (
        <Alert severity="error" onClose={() => setErr(null)}>
          {error instanceof Error ? error.message : err}
        </Alert>
      ) : null}
      {msg ? (
        <Alert severity="success" onClose={() => setMsg(null)}>
          {msg}
        </Alert>
      ) : null}

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
        <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
          Transactional Soft Wall outbox. Dead letters retry keeps the same idempotency key (no double-send invent).
          Dead letters: {data?.dead_letter_count ?? 0}
        </Typography>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="outbox-status">Status</InputLabel>
          <Select
            labelId="outbox-status"
            label="Status"
            value={status}
            onChange={(e) => setStatus(String(e.target.value))}
          >
            <MenuItem value="">All</MenuItem>
            {["pending", "sent", "failed", "dead_letter", "cancelled"].map((s) => (
              <MenuItem key={s} value={s}>
                {s}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button component="a" href="/outreach/approvals" size="small">
          Approvals
        </Button>
      </Stack>

      <Paper variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Status</TableCell>
              <TableCell>Kind</TableCell>
              <TableCell>Entity</TableCell>
              <TableCell>Idempotency</TableCell>
              <TableCell>Attempts</TableCell>
              <TableCell>Last error</TableCell>
              <TableCell>Updated</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!isLoading && items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8}>
                  <EmptyState
                    title="Outbox empty"
                    description="No pending, failed, or dead-letter Soft Wall sends for this workspace."
                  />
                </TableCell>
              </TableRow>
            ) : (
              items.map((row) => {
                const st = String(row.status || "");
                return (
                  <TableRow key={String(row.id)}>
                    <TableCell>{st}</TableCell>
                    <TableCell>{String(row.kind || "")}</TableCell>
                    <TableCell>
                      {row.entity_type ? (
                        <Button
                          component="a"
                          href={
                            row.entity_type === "lead"
                              ? `/outreach/leads/${row.entity_id}`
                              : `/crm`
                          }
                          size="small"
                        >
                          {String(row.entity_type)}/{String(row.entity_id || "").slice(0, 8)}
                        </Button>
                      ) : (
                        "-"
                      )}
                    </TableCell>
                    <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>
                      {String(row.idempotency_key || "").slice(0, 24)}
                    </TableCell>
                    <TableCell>{String(row.attempts ?? 0)}</TableCell>
                    <TableCell>{String(row.last_error || "")}</TableCell>
                    <TableCell sx={{ whiteSpace: "nowrap" }}>{String(row.updated_at || "")}</TableCell>
                    <TableCell align="right">
                      {(st === "dead_letter" || st === "failed") && (
                        <Button
                          size="small"
                          disabled={busyId === row.id}
                          onClick={() => void act(String(row.id), "retry")}
                        >
                          Retry
                        </Button>
                      )}
                      {(st === "pending" || st === "failed") && (
                        <Button
                          size="small"
                          color="warning"
                          disabled={busyId === row.id}
                          onClick={() => void act(String(row.id), "cancel")}
                        >
                          Cancel
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </Paper>
    </Stack>
  );
}
