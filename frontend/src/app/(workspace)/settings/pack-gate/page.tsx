"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { useCESession } from "@/lib/ce-auth";
import {
  fetchAdminUsers,
  fetchPackGateConfig,
  fetchPackGateRecords,
  savePackGateConfig,
  type PackGateRecord,
} from "@/lib/pack-gate-api";

function RecordsTable({ title, records }: { title: string; records: PackGateRecord[] }) {
  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>
        {title}
      </Typography>
      {records.length === 0 ? (
        <Typography color="text.secondary">No records.</Typography>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Pack</TableCell>
              <TableCell>Version</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Requested</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {records.map((record) => (
              <TableRow key={record.id}>
                <TableCell>{record.pack_id}</TableCell>
                <TableCell>
                  {record.from_version ? `${record.from_version} -> ` : ""}
                  {record.to_version}
                </TableCell>
                <TableCell>{record.status}</TableCell>
                <TableCell>{record.requested_at?.slice(0, 19) || "-"}</TableCell>
                <TableCell>
                  <Button component={Link} href={`/packs/${record.pack_id}/gate?record=${record.id}`} size="small">
                    Open
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Box>
  );
}

export default function PackGateSettingsPage() {
  const { user } = useCESession();
  const isAdmin = user?.role === "admin" || user?.role === "owner";
  const { data: config, mutate: mutateConfig } = useSWR(isAdmin ? "pack-gate-config" : null, fetchPackGateConfig);
  const { data: users } = useSWR(isAdmin ? "pack-gate-users" : null, fetchAdminUsers);
  const { data: pending } = useSWR(isAdmin ? "pack-gate-pending" : null, () =>
    fetchPackGateRecords({ status: "pending" }),
  );
  const { data: history } = useSWR(isAdmin ? "pack-gate-history" : null, () => fetchPackGateRecords());

  const [enabled, setEnabled] = React.useState(false);
  const [approverUserId, setApproverUserId] = React.useState("");
  const [notifyOnInstall, setNotifyOnInstall] = React.useState(true);
  const [requireChangelog, setRequireChangelog] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!config) return;
    setEnabled(config.enabled);
    setApproverUserId(config.approver_user_id || "");
    setNotifyOnInstall(config.notify_on_install);
    setRequireChangelog(config.require_changelog);
  }, [config]);

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader title="Pack gate" description="Clinical pack sign-off settings." />
        <Alert severity="warning">Admin access is required to configure the pack gate.</Alert>
      </Box>
    );
  }

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await savePackGateConfig({
        enabled,
        approver_user_id: approverUserId || null,
        notify_on_install: notifyOnInstall,
        require_changelog: requireChangelog,
      });
      setMessage("Pack gate configuration saved.");
      await mutateConfig();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const historyRows =
    history?.records.filter((row) => row.status === "approved" || row.status === "rejected").slice(0, 20) ?? [];

  return (
    <Box>
      <PageHeader
        title="Pack gate"
        description="Require documented sign-off before new pack versions activate in this workspace."
      />
      {enabled && !approverUserId ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Set an approver to complete gate configuration.
        </Alert>
      ) : null}
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}

      <FormControlLabel
        control={<Switch checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />}
        label="Require sign-off before activating new pack versions"
      />

      <FormControl fullWidth sx={{ mt: 3, maxWidth: 420 }}>
        <InputLabel id="approver-label">Approver</InputLabel>
        <Select
          labelId="approver-label"
          label="Approver"
          value={approverUserId}
          onChange={(e) => setApproverUserId(String(e.target.value))}
        >
          <MenuItem value="">
            <em>Select approver</em>
          </MenuItem>
          {(users ?? []).map((entry) => (
            <MenuItem key={entry.id} value={entry.id}>
              {entry.username}
              {entry.email ? ` (${entry.email})` : ""}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      <Box sx={{ mt: 2, display: "flex", flexDirection: "column", gap: 1 }}>
        <FormControlLabel
          control={<Checkbox checked={notifyOnInstall} onChange={(e) => setNotifyOnInstall(e.target.checked)} />}
          label="Notify on install"
        />
        <FormControlLabel
          control={<Checkbox checked={requireChangelog} onChange={(e) => setRequireChangelog(e.target.checked)} />}
          label="Require changelog"
        />
      </Box>

      <Button sx={{ mt: 3 }} variant="contained" onClick={() => void handleSave()} disabled={saving}>
        {saving ? "Saving..." : "Save configuration"}
      </Button>

      <RecordsTable title="Pending approvals" records={pending?.records ?? []} />
      <RecordsTable title="Recent approval history" records={historyRows} />
    </Box>
  );
}
