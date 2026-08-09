"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import FormControl from "@mui/material/FormControl";
import Grid from "@mui/material/Grid2";
import InputLabel from "@mui/material/InputLabel";
import Link from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import {
  applyCrmSheetJob,
  approveCrmApproval,
  fetchCrmSheetJob,
  listCrmSheetJobs,
  proposeCrmSheet,
  rejectCrmApproval,
  type SheetEnrichJob,
  uploadCrmSheet,
  crmSheetDownloadUrl,
  importCrmGoogleSheet,
  publishCrmGoogleSheet,
} from "@/lib/crm-api";
import { CRM_WORKSPACE, type CrmApproval } from "@/components/crm/types";
import CrmLicensedEnrichPanel from "@/components/crm/CrmLicensedEnrichPanel";
import PageHeader from "@/components/ui/PageHeader";

const COLUMN_ROLES = [
  "identity",
  "metric",
  "enrich_target",
  "pii",
  "ignore",
  "score",
  "stage",
  "contact_email",
  "contact_phone",
  "company_name",
  "url",
] as const;

type ColumnMap = Record<string, string>;

function proposalInner(job: SheetEnrichJob | null): Record<string, unknown> | null {
  const blob = job?.proposal;
  if (!blob || typeof blob !== "object") return null;
  const inner = (blob as { proposal?: Record<string, unknown> }).proposal;
  if (inner && typeof inner === "object") return inner;
  return blob as Record<string, unknown>;
}

function columnsFromJob(job: SheetEnrichJob | null): ColumnMap {
  const proposal = proposalInner(job);
  const cols = (proposal?.columns || {}) as Record<string, { role?: string } | string>;
  const out: ColumnMap = {};
  for (const [name, spec] of Object.entries(cols)) {
    if (typeof spec === "string") out[name] = spec;
    else out[name] = String(spec?.role || "metric");
  }
  return out;
}

function fillsFromJob(job: SheetEnrichJob | null): Array<Record<string, unknown>> {
  const proposal = proposalInner(job);
  const fills = proposal?.fills;
  return Array.isArray(fills) ? (fills as Array<Record<string, unknown>>) : [];
}

function jobStep(job: SheetEnrichJob | null, uploadId: string | null, pending: boolean): number {
  if (!job && !uploadId) return 0;
  if (!job && uploadId) return 1;
  const status = String(job?.status || "").toLowerCase();
  if (status === "applied") return 4;
  if (pending || status.includes("pending") || status.includes("approval")) return 3;
  if (Object.keys(columnsFromJob(job)).length > 0 || fillsFromJob(job).length > 0) return 2;
  return 1;
}

const STEPS = [
  { id: 0, label: "Upload" },
  { id: 1, label: "Propose" },
  { id: 2, label: "Map & review" },
  { id: 3, label: "Soft Wall" },
  { id: 4, label: "Applied" },
] as const;

function MetricTile({ label, value }: { label: string; value: string | number }) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h5" sx={{ mt: 0.5, fontVariantNumeric: "tabular-nums" }}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default function CrmEnrichPage() {
  const search = useSearchParams();
  const workspaceId = CRM_WORKSPACE;
  const jobFromUrl = search.get("job") || "";
  const approvalFromUrl = search.get("approval") || "";

  const [file, setFile] = React.useState<File | null>(null);
  const [uploadId, setUploadId] = React.useState<string | null>(null);
  const [googleSheetId, setGoogleSheetId] = React.useState("");
  const [job, setJob] = React.useState<SheetEnrichJob | null>(null);
  const [columnMap, setColumnMap] = React.useState<ColumnMap>({});
  const [pendingApproval, setPendingApproval] = React.useState<CrmApproval | null>(null);
  const [recent, setRecent] = React.useState<SheetEnrichJob[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [listLink, setListLink] = React.useState<string | null>(null);

  const loadJob = React.useCallback(
    async (id: string) => {
      const res = await fetchCrmSheetJob(id, workspaceId);
      setJob(res.enrichment_job);
      setColumnMap(columnsFromJob(res.enrichment_job));
      const apply = res.enrichment_job.apply_result as { crm?: { list_id?: string } } | undefined;
      const listId = apply?.crm?.list_id;
      setListLink(listId ? `/crm/lists/${listId}` : null);
      return res.enrichment_job;
    },
    [workspaceId],
  );

  React.useEffect(() => {
    void (async () => {
      try {
        const listed = await listCrmSheetJobs(workspaceId);
        setRecent(listed.items.slice(0, 12));
      } catch {
        /* ignore list errors on mount */
      }
      if (jobFromUrl) {
        try {
          await loadJob(jobFromUrl);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Could not load job");
        }
      }
    })();
  }, [jobFromUrl, loadJob, workspaceId]);

  const metrics = job?.metrics || {
    blank_cells: 0,
    proposed_fills: 0,
    cells_filled: 0,
    cost_estimate: job?.cost_estimate,
    row_count: 0,
  };
  const fills = fillsFromJob(job);
  const warnings = (proposalInner(job)?.warnings as string[] | undefined) || [];
  const activeStep = jobStep(job, uploadId, Boolean(pendingApproval || approvalFromUrl));

  const onUpload = async () => {
    if (!file) {
      setError("Choose a CSV or XLSX file first");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    setPendingApproval(null);
    setListLink(null);
    try {
      const uploaded = await uploadCrmSheet(file, workspaceId);
      setUploadId(uploaded.upload.upload_id);
      setMessage(`Uploaded ${uploaded.upload.filename}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  const onGoogleSheetImport = async () => {
    if (!googleSheetId.trim()) {
      setError("Enter a Google Sheet ID or URL first");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const match = googleSheetId.match(/\/spreadsheets\/d\/([^/]+)/);
      const spreadsheetId = match?.[1] || googleSheetId.trim();
      const imported = await importCrmGoogleSheet({ spreadsheet_id: spreadsheetId }, workspaceId);
      setUploadId(imported.upload.upload_id);
      setMessage(`Imported ${imported.upload.filename}; ready to convert and propose`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google Sheet import failed");
    } finally {
      setBusy(false);
    }
  };

  const onPublishGoogleSheet = async () => {
    if (!job?.id) return;
    setBusy(true);
    setError(null);
    try {
      const published = await publishCrmGoogleSheet(String(job.id), workspaceId);
      if (published.spreadsheet_url) window.open(published.spreadsheet_url, "_blank", "noopener,noreferrer");
      setMessage("Google Sheet created in the connected account");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google Sheet export failed");
    } finally {
      setBusy(false);
    }
  };

  const onPropose = async () => {
    if (!uploadId && !job?.source_path) {
      setError("Upload a spreadsheet first");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    setPendingApproval(null);
    try {
      const body: {
        upload_id?: string;
        user_schema?: Record<string, string>;
        domain_pack?: string;
        build_crm_plan?: boolean;
      } = {
        domain_pack: "generic",
        build_crm_plan: true,
      };
      if (uploadId) body.upload_id = uploadId;
      if (Object.keys(columnMap).length > 0) body.user_schema = columnMap;
      const res = await proposeCrmSheet(body, workspaceId);
      setJob(res.enrichment_job);
      setColumnMap(columnsFromJob(res.enrichment_job));
      setMessage(`Proposal ready (${res.enrichment_job.id})`);
      const listed = await listCrmSheetJobs(workspaceId);
      setRecent(listed.items.slice(0, 12));
      if (typeof window !== "undefined" && res.enrichment_job.id) {
        const url = new URL(window.location.href);
        url.searchParams.set("job", String(res.enrichment_job.id));
        window.history.replaceState({}, "", url.toString());
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Propose failed");
    } finally {
      setBusy(false);
    }
  };

  const onRequestApply = async () => {
    if (!job?.id) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await applyCrmSheetJob(
        String(job.id),
        { approval_id: approvalFromUrl || pendingApproval?.id || undefined, upsert_crm: true },
        workspaceId,
      );
      if (res.blocked) {
        setPendingApproval(res.approval || null);
        setMessage("Soft Wall approval required before apply");
        return;
      }
      if (res.enrichment_job) {
        setJob(res.enrichment_job);
        setListLink(res.list_deep_link || null);
      }
      setPendingApproval(null);
      setMessage("Enrichment applied; CRM upsert complete where planned");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Apply failed");
    } finally {
      setBusy(false);
    }
  };

  const onApproveThenApply = async () => {
    const approvalId = pendingApproval?.id || approvalFromUrl;
    if (!approvalId || !job?.id) return;
    setBusy(true);
    setError(null);
    try {
      await approveCrmApproval(approvalId, workspaceId);
      const res = await applyCrmSheetJob(
        String(job.id),
        { approval_id: approvalId, upsert_crm: true },
        workspaceId,
      );
      if (res.blocked) {
        setPendingApproval(res.approval || null);
        setError(res.error_code || "Still blocked after approve");
        return;
      }
      if (res.enrichment_job) setJob(res.enrichment_job);
      setListLink(res.list_deep_link || null);
      setPendingApproval(null);
      setMessage("Approved and applied");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve/apply failed");
    } finally {
      setBusy(false);
    }
  };

  const onReject = async () => {
    const approvalId = pendingApproval?.id || approvalFromUrl;
    if (!approvalId) {
      setError("No pending Soft Wall approval to reject");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await rejectCrmApproval(approvalId, workspaceId);
      setPendingApproval(null);
      setMessage("Rejected; sheet and CRM store left unchanged");
      if (job?.id) await loadJob(String(job.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Enrich"
        description="Fill blank spreadsheet cells and licensed lead fields. Soft Wall gates every write. Existing values are never overwritten by default."
        breadcrumbs={[
          { label: "CRM", href: "/crm" },
          { label: "Enrich" },
        ]}
        actions={
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button component="a" href="/crm/settings" size="small" variant="outlined">
              Provider keys
            </Button>
            <Button component="a" href="/crm/jobs" size="small" variant="outlined">
              Jobs
            </Button>
            <Button component="a" href="/crm/lists" size="small" variant="outlined">
              Lists
            </Button>
          </Stack>
        }
      />

      <Card variant="outlined">
        <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
          <Stack
            direction="row"
            spacing={1}
            flexWrap="wrap"
            useFlexGap
            alignItems="center"
            sx={{ rowGap: 1 }}
          >
            {STEPS.map((step, index) => {
              const done = activeStep > step.id;
              const current = activeStep === step.id;
              return (
                <React.Fragment key={step.id}>
                  {index > 0 ? (
                    <Box sx={{ width: 18, height: 2, bgcolor: done || current ? "primary.main" : "divider", display: { xs: "none", sm: "block" } }} />
                  ) : null}
                  <Chip
                    size="small"
                    label={`${step.id + 1}. ${step.label}`}
                    color={current ? "primary" : done ? "success" : "default"}
                    variant={current || done ? "filled" : "outlined"}
                  />
                </React.Fragment>
              );
            })}
          </Stack>
        </CardContent>
      </Card>

      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Box>
        <Typography variant="overline" color="text.secondary">
          Sheet preprocess
        </Typography>
        <Typography variant="h6" component="h2" sx={{ mt: 0.25, mb: 1.5 }}>
          Spreadsheet enrich
        </Typography>

        <Card
          variant="outlined"
          sx={{
            mb: 2,
            borderStyle: "dashed",
            bgcolor: "action.hover",
          }}
        >
          <CardContent>
            <Stack spacing={1.5}>
              <Typography variant="subtitle1">1. Upload spreadsheet</Typography>
              <Typography variant="body2" color="text.secondary">
                CSV, TSV, XLSX, or a connected Google Sheet. Keprix converts the selected worksheet to a canonical
                table for processing, then offers Excel, Google Sheets, or CSV delivery.
              </Typography>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }}>
                <Button variant="outlined" component="label" disabled={busy}>
                  Choose file
                  <input
                    hidden
                    type="file"
                    accept=".csv,.tsv,.xlsx"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
                </Button>
                <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
                  {file ? file.name : "No file selected"}
                </Typography>
                <Button variant="contained" disabled={busy || !file} onClick={() => void onUpload()}>
                  Upload
                </Button>
                <Button
                  variant="contained"
                  color="secondary"
                  disabled={busy || (!uploadId && !job)}
                  onClick={() => void onPropose()}
                >
                  Propose
                </Button>
              </Stack>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }}>
                <TextField
                  fullWidth
                  size="small"
                  label="Google Sheet URL or ID"
                  value={googleSheetId}
                  onChange={(event) => setGoogleSheetId(event.target.value)}
                />
                <Button variant="outlined" disabled={busy || !googleSheetId.trim()} onClick={() => void onGoogleSheetImport()}>
                  Import Google Sheet
                </Button>
              </Stack>
              {uploadId ? (
                <Chip size="small" variant="outlined" label={`Upload ready · ${uploadId}`} sx={{ alignSelf: "flex-start" }} />
              ) : null}
            </Stack>
          </CardContent>
        </Card>

        {!job ? (
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={1.25} alignItems="flex-start">
                <Typography variant="subtitle1">No active sheet job</Typography>
                <Typography variant="body2" color="text.secondary">
                  Upload a file and click Propose to open column mapping, blank-cell review, and Soft Wall apply.
                  Or reopen a recent job from the table below.
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  <Chip size="small" label="Empty cells only" variant="outlined" />
                  <Chip size="small" label="Soft Wall required" variant="outlined" />
                  <Chip size="small" label="Optional CRM upsert" variant="outlined" />
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        ) : (
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Chip label={String(job.status || "unknown")} color="primary" size="small" />
              <Chip label={String(job.sheet_type || "generic")} size="small" variant="outlined" />
              <Chip label={`Job ${job.id}`} size="small" variant="outlined" />
            </Stack>

            <Grid container spacing={1.5}>
              <Grid size={{ xs: 6, sm: 4, md: 2 }}>
                <MetricTile label="Blank cells" value={metrics.blank_cells ?? 0} />
              </Grid>
              <Grid size={{ xs: 6, sm: 4, md: 2 }}>
                <MetricTile label="Proposed fills" value={metrics.proposed_fills ?? 0} />
              </Grid>
              <Grid size={{ xs: 6, sm: 4, md: 2 }}>
                <MetricTile label="Filled" value={metrics.cells_filled ?? 0} />
              </Grid>
              <Grid size={{ xs: 6, sm: 4, md: 3 }}>
                <MetricTile label="Rows" value={metrics.row_count ?? 0} />
              </Grid>
              <Grid size={{ xs: 6, sm: 4, md: 3 }}>
                <MetricTile label="Cost estimate" value={metrics.cost_estimate ?? job.cost_estimate ?? 0} />
              </Grid>
            </Grid>

            {warnings.length > 0 ? (
              <Alert severity="warning">
                {warnings.map((w) => (
                  <Typography key={w} variant="body2">
                    {w}
                  </Typography>
                ))}
              </Alert>
            ) : null}

            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>
                  2. Column mapper
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  Adjust roles, then re-run Propose to lock the schema. Soft Wall apply is still required.
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Column</TableCell>
                        <TableCell sx={{ width: { xs: "50%", sm: 280 } }}>Role</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.keys(columnMap).length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={2}>
                            <Typography color="text.secondary">No columns yet. Run Propose after upload.</Typography>
                          </TableCell>
                        </TableRow>
                      ) : (
                        Object.entries(columnMap).map(([name, role]) => (
                          <TableRow key={name} hover>
                            <TableCell>
                              <Typography variant="body2" fontWeight={600}>
                                {name}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <FormControl size="small" fullWidth>
                                <InputLabel id={`role-${name}`}>Role</InputLabel>
                                <Select
                                  labelId={`role-${name}`}
                                  label="Role"
                                  value={role}
                                  onChange={(e) =>
                                    setColumnMap((prev) => ({ ...prev, [name]: String(e.target.value) }))
                                  }
                                >
                                  {COLUMN_ROLES.map((r) => (
                                    <MenuItem key={r} value={r}>
                                      {r}
                                    </MenuItem>
                                  ))}
                                </Select>
                              </FormControl>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
                <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
                  <Button size="small" variant="outlined" disabled={busy || (!uploadId && !job)} onClick={() => void onPropose()}>
                    Re-propose with map
                  </Button>
                </Stack>
              </CardContent>
            </Card>

            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>
                  3. Blank report and proposed fills
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  Blank cells surveyed: {metrics.blank_cells ?? 0}. Values below are review-only until Soft Wall approve.
                </Typography>
                {fills.length === 0 ? (
                  <Alert severity="info" variant="outlined">
                    No model fills proposed (schema-only analyser). CRM upsert may still create leads from identity
                    columns when you apply.
                  </Alert>
                ) : (
                  <TableContainer sx={{ maxHeight: 360 }}>
                    <Table size="small" stickyHeader>
                      <TableHead>
                        <TableRow>
                          <TableCell>Row</TableCell>
                          <TableCell>Column</TableCell>
                          <TableCell>Proposed value</TableCell>
                          <TableCell>Confidence</TableCell>
                          <TableCell>Evidence</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {fills.slice(0, 80).map((fill, idx) => (
                          <TableRow key={`${fill.row_index}-${fill.column}-${idx}`} hover>
                            <TableCell>{String(fill.row_index)}</TableCell>
                            <TableCell>{String(fill.column)}</TableCell>
                            <TableCell>{String(fill.value ?? "")}</TableCell>
                            <TableCell>
                              {fill.confidence === undefined || fill.confidence === null
                                ? "-"
                                : String(fill.confidence)}
                            </TableCell>
                            <TableCell>{String(fill.evidence || "")}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </CardContent>
            </Card>

            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>
                  4. Soft Wall apply
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  Request apply opens Soft Wall. Approve to write fills and optional CRM upsert, or reject to leave
                  the sheet unchanged.
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
                  <Button
                    variant="contained"
                    disabled={busy || job.status === "applied"}
                    onClick={() => void onRequestApply()}
                  >
                    Request apply
                  </Button>
                  <Button
                    variant="contained"
                    color="success"
                    disabled={busy || (!pendingApproval && !approvalFromUrl)}
                    onClick={() => void onApproveThenApply()}
                  >
                    Approve and apply
                  </Button>
                  <Button
                    variant="outlined"
                    color="inherit"
                    disabled={busy || (!pendingApproval && !approvalFromUrl)}
                    onClick={() => void onReject()}
                  >
                    Reject
                  </Button>
                  {job.status === "applied" && job.output_path ? (
                    <>
                      <Button component="a" href={crmSheetDownloadUrl(String(job.id), "xlsx", workspaceId)} variant="outlined">
                        Download Excel
                      </Button>
                      <Button component="a" href={crmSheetDownloadUrl(String(job.id), "csv", workspaceId)} variant="outlined">
                        Download CSV
                      </Button>
                      <Button variant="outlined" disabled={busy} onClick={() => void onPublishGoogleSheet()}>
                        Create Google Sheet
                      </Button>
                    </>
                  ) : null}
                </Stack>
                {pendingApproval ? (
                  <Alert severity="warning" sx={{ mb: 1 }}>
                    Soft Wall pending: {pendingApproval.subject || pendingApproval.id}
                  </Alert>
                ) : null}
                {listLink ? (
                  <Typography variant="body2">
                    Resulting list:{" "}
                    <Link component="a" href={listLink}>
                      {listLink}
                    </Link>
                    {" · "}
                    <Link component="a" href="/crm/leads">
                      View leads
                    </Link>
                  </Typography>
                ) : job.status === "applied" ? (
                  <Typography variant="body2">
                    <Link component="a" href="/crm/leads">
                      View leads
                    </Link>
                  </Typography>
                ) : null}
              </CardContent>
            </Card>
          </Stack>
        )}
      </Box>

      <Divider />

      <Box>
        <Typography variant="overline" color="text.secondary">
          Lead enrichment
        </Typography>
        <Typography variant="h6" component="h2" sx={{ mt: 0.25, mb: 1.5 }}>
          Licensed providers
        </Typography>
        <CrmLicensedEnrichPanel />
      </Box>

      <Card variant="outlined">
        <CardContent>
          <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={1} sx={{ mb: 1.5 }}>
            <Box>
              <Typography variant="subtitle1">Recent sheet jobs</Typography>
              <Typography variant="body2" color="text.secondary">
                Reopen a job to continue mapping, Soft Wall, or download.
              </Typography>
            </Box>
            <Button size="small" component="a" href="/crm/jobs" variant="text">
              All CRM jobs
            </Button>
          </Stack>
          {recent.length === 0 ? (
            <Typography color="text.secondary">No enrichment jobs yet. Upload a sheet to start.</Typography>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Job</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell align="right">Open</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {recent.map((item) => (
                    <TableRow key={String(item.id)} hover>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {String(item.id)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip size="small" label={String(item.status || "unknown")} variant="outlined" />
                      </TableCell>
                      <TableCell>{String(item.sheet_type || "generic")}</TableCell>
                      <TableCell align="right">
                        <Link component="a" href={`/crm/enrich?job=${item.id}`} underline="hover">
                          Open
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
