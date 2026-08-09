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
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { SkeletonList, SkeletonTable } from "@/components/ui/loading";
import { useCESession } from "@/lib/ce-auth";
import {
  type ReadinessCategory,
  type ReadinessCheck,
  type ReadinessStatus,
  createReadinessBackup,
  fetchReadinessReport,
  fetchRestoreEvidence,
  recordRestoreEvidence,
} from "@/lib/readiness-api";

function isAdminRole(role: string | undefined): boolean {
  const r = (role || "").toLowerCase();
  return r === "admin" || r === "owner" || r === "superadmin" || r === "developer";
}

function statusColor(status?: ReadinessStatus): "success" | "warning" | "error" | "default" {
  if (status === "pass") return "success";
  if (status === "warn") return "warning";
  if (status === "fail") return "error";
  return "default";
}

function StatusChip({ status, label }: { status?: ReadinessStatus; label?: string }) {
  return (
    <Chip
      size="small"
      label={label || status || "unknown"}
      color={statusColor(status)}
      variant={status === "pass" ? "filled" : "outlined"}
    />
  );
}

function CategoryCard({
  title,
  status,
  checks,
}: {
  title: string;
  status?: ReadinessStatus;
  checks: ReadinessCheck[];
}) {
  const failing = checks.filter((c) => c.status === "fail" || c.status === "warn");
  return (
    <Paper variant="outlined" sx={{ p: 2, height: "100%" }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="subtitle1">{title}</Typography>
        <StatusChip status={status} />
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        {checks.length} checks · {failing.length} need attention
      </Typography>
      <Stack spacing={0.75}>
        {failing.slice(0, 4).map((check) => (
          <Typography key={check.id} variant="caption" color="text.secondary">
            {check.title}: {check.status}
          </Typography>
        ))}
        {failing.length === 0 ? (
          <Typography variant="caption" color="text.secondary">
            No warnings or failures in this category.
          </Typography>
        ) : null}
      </Stack>
    </Paper>
  );
}

export default function AdminReadinessPage() {
  const { user, isLoading: sessionLoading } = useCESession();
  const isAdmin = isAdminRole(user?.role);
  const [tab, setTab] = React.useState(0);
  const [category, setCategory] = React.useState<ReadinessCategory | "all">("all");
  const [targetVersion, setTargetVersion] = React.useState("");
  const [appliedTarget, setAppliedTarget] = React.useState<string | undefined>(undefined);
  const [selected, setSelected] = React.useState<ReadinessCheck | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [confirmBackup, setConfirmBackup] = React.useState(false);
  const [backupPassword, setBackupPassword] = React.useState("");
  const [evidenceNote, setEvidenceNote] = React.useState("");
  const [evidenceBackupId, setEvidenceBackupId] = React.useState("");

  const report = useSWR(isAdmin ? ["admin-readiness", appliedTarget || ""] : null, () =>
    fetchReadinessReport(appliedTarget),
  );
  const evidence = useSWR(isAdmin ? "admin-restore-evidence" : null, () => fetchRestoreEvidence(20));

  const checks = React.useMemo(() => {
    const rows = report.data?.checks ?? [];
    if (category === "all") return rows;
    return rows.filter((c) => c.category === category);
  }, [report.data, category]);

  if (sessionLoading) {
    return (
      <Box>
        <PageHeader title="Readiness" description="Deployment readiness checks." />
        <SkeletonList rows={4} rowHeight={48} />
      </Box>
    );
  }

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader
          title="Readiness"
          description="Deployment readiness checks for this workspace."
          breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Readiness" }]}
        />
        <Alert severity="error">Admin role required to view readiness gates.</Alert>
      </Box>
    );
  }

  async function runBackup() {
    setBusy(true);
    setError(null);
    try {
      const result = await createReadinessBackup({
        password: backupPassword.trim() || null,
        timeoutSec: 120,
      });
      if (result.ok === false) {
        throw new Error(String(result.error || result.failure_reason || "Backup failed"));
      }
      setMessage(`Backup created${result.id ? `: ${String(result.id)}` : ""}.`);
      setConfirmBackup(false);
      setBackupPassword("");
      await report.mutate();
      await evidence.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backup failed");
    } finally {
      setBusy(false);
    }
  }

  async function addEvidence() {
    setBusy(true);
    setError(null);
    try {
      await recordRestoreEvidence({
        ok: true,
        backup_id: evidenceBackupId.trim() || null,
        restored_files: 0,
        encrypted: Boolean(backupPassword),
        note: evidenceNote.trim() || "Operator recorded restore evidence from readiness UI",
      });
      setMessage("Restore evidence recorded.");
      setEvidenceNote("");
      setEvidenceBackupId("");
      await evidence.mutate();
      await report.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record evidence");
    } finally {
      setBusy(false);
    }
  }

  const data = report.data;

  return (
    <Box>
      <PageHeader
        title="Readiness"
        description="Market, upgrade, and recovery gates for this instance. Failed checks include a fix path for admin navigation."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Readiness" }]}
        actions={
          <Stack direction="row" spacing={1}>
            <Button component="a" href="/admin/backup" size="small" variant="outlined">
              Backups
            </Button>
            <Button size="small" variant="contained" onClick={() => setConfirmBackup(true)}>
              Safe backup
            </Button>
          </Stack>
        }
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}
      {report.error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {report.error.message}
        </Alert>
      ) : null}

      {report.isLoading || !data ? (
        <SkeletonList rows={5} rowHeight={72} />
      ) : (
        <>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mb: 2 }} alignItems={{ md: "center" }}>
            <StatusChip status={data.overall} label={`Overall: ${data.overall}`} />
            <Chip size="small" label={`pass ${data.counts?.pass ?? 0}`} color="success" variant="outlined" />
            <Chip size="small" label={`warn ${data.counts?.warn ?? 0}`} color="warning" variant="outlined" />
            <Chip size="small" label={`fail ${data.counts?.fail ?? 0}`} color="error" variant="outlined" />
            <Typography variant="caption" color="text.secondary">
              Generated {data.generated_at ? new Date(data.generated_at).toLocaleString() : ";"}
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <TextField
              size="small"
              label="Target version"
              placeholder="e.g. 0.16.0"
              value={targetVersion}
              onChange={(e) => setTargetVersion(e.target.value)}
              sx={{ width: 140 }}
            />
            <Button
              size="small"
              onClick={() => {
                setAppliedTarget(targetVersion.trim() || undefined);
                void report.mutate();
              }}
            >
              Refresh
            </Button>
          </Stack>

          {(data.notes || []).length > 0 ? (
            <Alert severity="info" sx={{ mb: 2 }}>
              {(data.notes || []).join(" ")}
            </Alert>
          ) : null}

          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" },
              mb: 2,
            }}
          >
            <CategoryCard
              title="Market"
              status={data.market}
              checks={(data.checks || []).filter((c) => c.category === "market")}
            />
            <CategoryCard
              title="Upgrade"
              status={data.upgrade}
              checks={(data.checks || []).filter((c) => c.category === "upgrade")}
            />
            <CategoryCard
              title="Recovery"
              status={data.recovery}
              checks={(data.checks || []).filter((c) => c.category === "recovery")}
            />
          </Box>

          <Tabs value={tab} onChange={(_, v: number) => setTab(v)} sx={{ mb: 2 }}>
            <Tab label="Checks" />
            <Tab label="Restore evidence" />
          </Tabs>

          {tab === 0 ? (
            <Stack spacing={2}>
              <FormControl size="small" sx={{ maxWidth: 220 }}>
                <InputLabel id="readiness-category">Category</InputLabel>
                <Select
                  labelId="readiness-category"
                  label="Category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value as ReadinessCategory | "all")}
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="market">Market</MenuItem>
                  <MenuItem value="upgrade">Upgrade</MenuItem>
                  <MenuItem value="recovery">Recovery</MenuItem>
                </Select>
              </FormControl>

              {checks.length === 0 ? (
                <EmptyState title="No checks" description="Readiness report returned no checks for this filter." />
              ) : (
                <Paper variant="outlined" sx={{ overflow: "auto" }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Check</TableCell>
                        <TableCell>Category</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Summary</TableCell>
                        <TableCell>Fix</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {checks.map((check) => (
                        <TableRow
                          key={check.id}
                          hover
                          selected={selected?.id === check.id}
                          onClick={() => setSelected(check)}
                          sx={{ cursor: "pointer" }}
                        >
                          <TableCell>
                            <Typography variant="subtitle2">{check.title}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {check.id}
                            </Typography>
                          </TableCell>
                          <TableCell>{check.category}</TableCell>
                          <TableCell>
                            <StatusChip status={check.status} />
                          </TableCell>
                          <TableCell sx={{ maxWidth: 360 }}>{check.summary}</TableCell>
                          <TableCell>
                            {check.fix_path ? (
                              <Button
                                component="a"
                                href={check.fix_path}
                                size="small"
                                onClick={(e) => e.stopPropagation()}
                              >
                                Open
                              </Button>
                            ) : (
                              ";"
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Paper>
              )}

              {selected ? (
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle1" sx={{ mb: 1 }}>
                    {selected.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {selected.summary}
                  </Typography>
                  {selected.docs_path ? (
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                      Docs: {selected.docs_path}
                    </Typography>
                  ) : null}
                  <StructuredDataView value={selected.evidence || {}} emptyLabel="No evidence payload" />
                </Paper>
              ) : null}
            </Stack>
          ) : null}

          {tab === 1 ? (
            <Stack spacing={2}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Record restore evidence
                </Typography>
                <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "flex-end" }}>
                  <TextField
                    size="small"
                    label="Backup id"
                    value={evidenceBackupId}
                    onChange={(e) => setEvidenceBackupId(e.target.value)}
                  />
                  <TextField
                    size="small"
                    label="Note"
                    value={evidenceNote}
                    onChange={(e) => setEvidenceNote(e.target.value)}
                    sx={{ minWidth: 280 }}
                  />
                  <Button variant="contained" disabled={busy} onClick={() => void addEvidence()}>
                    Record
                  </Button>
                </Stack>
              </Paper>

              {evidence.isLoading ? (
                <SkeletonTable rows={4} columns={5} />
              ) : (evidence.data?.evidence ?? []).length === 0 ? (
                <EmptyState
                  title="No restore evidence yet"
                  description="After a restore drill, record evidence here so the recovery readiness gate can pass."
                />
              ) : (
                <Paper variant="outlined" sx={{ overflow: "auto" }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>When</TableCell>
                        <TableCell>Backup</TableCell>
                        <TableCell>OK</TableCell>
                        <TableCell>Files</TableCell>
                        <TableCell>Note</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {(evidence.data?.evidence || []).map((row, idx) => (
                        <TableRow key={`${row.created_at}-${idx}`}>
                          <TableCell>
                            {typeof row.created_at === "number"
                              ? new Date(row.created_at * 1000).toLocaleString()
                              : row.created_at
                                ? String(row.created_at)
                                : ";"}
                          </TableCell>
                          <TableCell>{row.backup_id || ";"}</TableCell>
                          <TableCell>{row.ok ? "yes" : "no"}</TableCell>
                          <TableCell>{row.restored_files ?? 0}</TableCell>
                          <TableCell>{row.note || ";"}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Paper>
              )}
            </Stack>
          ) : null}
        </>
      )}

      <Dialog open={confirmBackup} onClose={() => (!busy ? setConfirmBackup(false) : undefined)}>
        <DialogTitle>Create safe backup?</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Runs the readiness-safe backup path with a timeout so the UI does not hang. Optional
            password encrypts the archive when supported.
          </DialogContentText>
          <TextField
            fullWidth
            size="small"
            type="password"
            label="Optional password"
            value={backupPassword}
            onChange={(e) => setBackupPassword(e.target.value)}
            autoComplete="new-password"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmBackup(false)} disabled={busy}>
            Cancel
          </Button>
          <Button variant="contained" onClick={() => void runBackup()} disabled={busy}>
            {busy ? "Working…" : "Create backup"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
