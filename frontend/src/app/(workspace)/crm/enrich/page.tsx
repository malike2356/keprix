"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Link from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
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
} from "@/lib/crm-api";
import { CRM_WORKSPACE, type CrmApproval } from "@/components/crm/types";
import CrmLicensedEnrichPanel from "@/components/crm/CrmLicensedEnrichPanel";

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

export default function CrmEnrichPage() {
  const search = useSearchParams();
  const workspaceId = CRM_WORKSPACE;
  const jobFromUrl = search.get("job") || "";
  const approvalFromUrl = search.get("approval") || "";

  const [file, setFile] = React.useState<File | null>(null);
  const [uploadId, setUploadId] = React.useState<string | null>(null);
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
        setRecent(listed.items.slice(0, 8));
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
      setRecent(listed.items.slice(0, 8));
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
    <Stack spacing={2.5}>
      <CrmLicensedEnrichPanel />
      <Box>
        <Typography variant="h5" component="h1" gutterBottom>
          Enrich
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Upload a spreadsheet, map columns, review blank-cell proposals, Soft Wall approve, then apply
          fills and optional CRM upsert. Empty cells only; never overwrites existing values by default.
        </Typography>
      </Box>

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

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            1. Upload
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems="flex-start">
            <Button variant="outlined" component="label" disabled={busy}>
              Choose file
              <input
                hidden
                type="file"
                accept=".csv,.tsv,.xlsx"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </Button>
            <Typography variant="body2" color="text.secondary" sx={{ pt: 0.75 }}>
              {file ? file.name : "CSV, TSV, or XLSX"}
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
          {uploadId ? (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
              upload_id: {uploadId}
            </Typography>
          ) : null}
        </CardContent>
      </Card>

      {job ? (
        <>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
                <Chip label={`status: ${job.status || "unknown"}`} size="small" />
                <Chip label={`type: ${job.sheet_type || "generic"}`} size="small" variant="outlined" />
                <Chip label={`job: ${job.id}`} size="small" variant="outlined" />
              </Stack>
              <Typography variant="subtitle1" gutterBottom>
                Metrics
              </Typography>
              <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
                <Typography variant="body2">Blank cells: {metrics.blank_cells ?? 0}</Typography>
                <Typography variant="body2">Proposed fills: {metrics.proposed_fills ?? 0}</Typography>
                <Typography variant="body2">Filled: {metrics.cells_filled ?? 0}</Typography>
                <Typography variant="body2">Rows: {metrics.row_count ?? 0}</Typography>
                <Typography variant="body2">
                  Cost estimate: {metrics.cost_estimate ?? job.cost_estimate ?? 0}
                </Typography>
              </Stack>
              {warnings.length > 0 ? (
                <Box sx={{ mt: 1.5 }}>
                  {warnings.map((w) => (
                    <Typography key={w} variant="caption" color="warning.main" display="block">
                      {w}
                    </Typography>
                  ))}
                </Box>
              ) : null}
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                2. Column mapper
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                Adjust roles then re-run Propose to lock a user schema. Soft Wall apply still required.
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Column</TableCell>
                    <TableCell>Role</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.keys(columnMap).length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={2}>
                        <Typography color="text.secondary">No columns yet.</Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    Object.entries(columnMap).map(([name, role]) => (
                      <TableRow key={name}>
                        <TableCell>{name}</TableCell>
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
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                3. Blank report and proposed fills
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Blank cells surveyed: {metrics.blank_cells ?? 0}. Proposed fills below are review-only until Soft
                Wall approve.
              </Typography>
              {fills.length === 0 ? (
                <Typography color="text.secondary">
                  No model fills proposed (schema-only analyser). CRM upsert plan may still create leads from
                  existing identity columns on apply.
                </Typography>
              ) : (
                <Table size="small">
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
                    {fills.slice(0, 50).map((fill, idx) => (
                      <TableRow key={`${fill.row_index}-${fill.column}-${idx}`}>
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
              )}
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                4. Soft Wall apply
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
                  <Button
                    component="a"
                    href={crmSheetDownloadUrl(String(job.id), workspaceId)}
                    variant="outlined"
                  >
                    Download enriched file
                  </Button>
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
                  <Link component={NextLink} href={listLink}>
                    {listLink}
                  </Link>
                  {" · "}
                  <Link component={NextLink} href="/crm/leads">
                    View leads
                  </Link>
                </Typography>
              ) : job.status === "applied" ? (
                <Typography variant="body2">
                  <Link component={NextLink} href="/crm/leads">
                    View leads
                  </Link>
                </Typography>
              ) : null}
            </CardContent>
          </Card>
        </>
      ) : null}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Recent sheet jobs
          </Typography>
          {recent.length === 0 ? (
            <Typography color="text.secondary">No enrichment jobs yet.</Typography>
          ) : (
            <Stack spacing={0.75}>
              {recent.map((item) => (
                <Link
                  key={String(item.id)}
                  component={NextLink}
                  href={`/crm/enrich?job=${item.id}`}
                  underline="hover"
                >
                  {item.id} · {item.status} · {item.sheet_type || "generic"}
                </Link>
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
