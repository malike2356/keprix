"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Rating from "@mui/material/Rating";
import Select from "@mui/material/Select";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import { useCESession } from "@/lib/ce-auth";
import {
  approveCorrection,
  batchApproveCorrections,
  fetchCorrection,
  fetchCorrections,
  rejectCorrection,
  type LocalizationCorrection,
} from "@/lib/localization-corrections-api";

const CORRECTION_TYPES = [
  "transcription",
  "translation",
  "intent",
  "entity",
  "response_translation",
  "glossary_addition",
] as const;

const LANGUAGE_OPTIONS = [
  { code: "", label: "All languages" },
  { code: "ak-GH", label: "Twi (ak-GH)" },
  { code: "en-GH", label: "English (en-GH)" },
  { code: "ee-GH", label: "Ewe (ee-GH)" },
  { code: "ha-GH", label: "Hausa (ha-GH)" },
];

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "-";
  return value.slice(0, 19).replace("T", " ");
}

function AuditContext({ audit }: { audit: Record<string, unknown> | null | undefined }) {
  if (!audit) {
    return <Typography color="text.secondary">No linked audit record.</Typography>;
  }
  const fields: Array<{ label: string; key: string }> = [
    { label: "Original input", key: "original_text" },
    { label: "Translated input", key: "translated_input" },
    { label: "Final response", key: "final_response" },
    { label: "Detected language", key: "detected_language" },
    { label: "Output language", key: "output_language" },
    { label: "Transcription provider", key: "transcription_provider" },
    { label: "Translation provider", key: "translation_provider" },
  ];
  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      {fields.map((field) => {
        const value = audit[field.key];
        if (!value) return null;
        return (
          <Box key={field.key}>
            <Typography variant="caption" color="text.secondary">
              {field.label}
            </Typography>
            <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
              {String(value)}
            </Typography>
          </Box>
        );
      })}
      {audit.human_review_required ? (
        <Chip size="small" color="warning" label="Human review was required" />
      ) : null}
    </Box>
  );
}

export default function LocalizationCorrectionsPage() {
  const { user } = useCESession();
  const isAdmin = user?.role === "admin" || user?.role === "owner";

  const [statusFilter, setStatusFilter] = React.useState("pending");
  const [typeFilter, setTypeFilter] = React.useState("");
  const [languageFilter, setLanguageFilter] = React.useState("");
  const [domainFilter, setDomainFilter] = React.useState("");

  const { data: corrections = [], mutate } = useSWR(
    `localization-corrections-${statusFilter}-${typeFilter}-${languageFilter}-${domainFilter}`,
    async () => {
      const rows = await fetchCorrections(statusFilter || undefined);
      return rows.filter((row) => {
        if (typeFilter && row.correction_type !== typeFilter) return false;
        if (languageFilter && row.source_language !== languageFilter) return false;
        if (domainFilter && row.domain !== domainFilter) return false;
        return true;
      });
    },
  );

  const [selectedIds, setSelectedIds] = React.useState<string[]>([]);
  const [detailId, setDetailId] = React.useState<string | null>(null);
  const [detail, setDetail] = React.useState<LocalizationCorrection | null>(null);
  const [editedValue, setEditedValue] = React.useState("");
  const [qualityScore, setQualityScore] = React.useState<number | null>(4);
  const [rejectReason, setRejectReason] = React.useState("");
  const [showReject, setShowReject] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [working, setWorking] = React.useState(false);

  const pendingSelectable = corrections.filter((row) => row.status === "pending");
  const allSelected = pendingSelectable.length > 0 && selectedIds.length === pendingSelectable.length;

  React.useEffect(() => {
    if (!detailId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    fetchCorrection(detailId)
      .then((record) => {
        if (cancelled) return;
        setDetail(record);
        setEditedValue(record.corrected_value);
        setQualityScore(4);
        setShowReject(false);
        setRejectReason("");
        setError(null);
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load correction");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [detailId]);

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds([]);
      return;
    }
    setSelectedIds(pendingSelectable.map((row) => row.id));
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  };

  const handleApprove = async () => {
    if (!detail || !qualityScore) {
      setError("Select a quality score before approving.");
      return;
    }
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      await approveCorrection(detail.id, qualityScore, editedValue.trim() || undefined);
      setMessage("Correction approved.");
      setDetailId(null);
      setSelectedIds((current) => current.filter((id) => id !== detail.id));
      await mutate();
    } catch (approveError) {
      setError(approveError instanceof Error ? approveError.message : "Approve failed");
    } finally {
      setWorking(false);
    }
  };

  const handleReject = async () => {
    if (!detail) return;
    if (!rejectReason.trim()) {
      setError("Enter a rejection reason.");
      return;
    }
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      await rejectCorrection(detail.id, rejectReason.trim());
      setMessage("Correction rejected.");
      setDetailId(null);
      setSelectedIds((current) => current.filter((id) => id !== detail.id));
      await mutate();
    } catch (rejectError) {
      setError(rejectError instanceof Error ? rejectError.message : "Reject failed");
    } finally {
      setWorking(false);
    }
  };

  const handleBatchApprove = async () => {
    if (!qualityScore || selectedIds.length === 0) {
      setError("Select corrections and a quality score.");
      return;
    }
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      await batchApproveCorrections(selectedIds, qualityScore);
      setMessage(`Approved ${selectedIds.length} correction(s).`);
      setSelectedIds([]);
      await mutate();
    } catch (batchError) {
      setError(batchError instanceof Error ? batchError.message : "Batch approve failed");
    } finally {
      setWorking(false);
    }
  };

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader
          title="Localization corrections"
          description="Review user-submitted translation and transcription fixes."
          breadcrumbs={[
            { label: "Settings", href: "/settings" },
            { label: "Corrections" },
          ]}
        />
        <Alert severity="warning">Admin access is required to review localization corrections.</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title="Localization corrections"
        description="Review corrections, apply glossary updates, and stage training samples."
        breadcrumbs={[
          { label: "Settings", href: "/settings" },
          { label: "Localization", href: "/settings/localization/metrics" },
          { label: "Corrections" },
        ]}
        actions={
          <Button component={Link} href="/settings/localization/metrics" size="small">
            View metrics
          </Button>
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

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent sx={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Status</InputLabel>
            <Select label="Status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <MenuItem value="">All</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="approved">Approved</MenuItem>
              <MenuItem value="rejected">Rejected</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Type</InputLabel>
            <Select label="Type" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
              <MenuItem value="">All types</MenuItem>
              {CORRECTION_TYPES.map((type) => (
                <MenuItem key={type} value={type}>
                  {type}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Language</InputLabel>
            <Select
              label="Language"
              value={languageFilter}
              onChange={(event) => setLanguageFilter(event.target.value)}
            >
              {LANGUAGE_OPTIONS.map((lang) => (
                <MenuItem key={lang.code || "all"} value={lang.code}>
                  {lang.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            size="small"
            label="Domain"
            value={domainFilter}
            onChange={(event) => setDomainFilter(event.target.value)}
            placeholder="borehole_drilling"
          />
        </CardContent>
      </Card>

      {selectedIds.length > 0 ? (
        <Card variant="outlined" sx={{ mb: 2 }}>
          <CardContent sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
            <Typography variant="body2">{selectedIds.length} selected</Typography>
            <Rating value={qualityScore} onChange={(_event, value) => setQualityScore(value)} />
            <Button variant="contained" size="small" disabled={working} onClick={() => void handleBatchApprove()}>
              Batch approve
            </Button>
            <Button size="small" onClick={() => setSelectedIds([])}>
              Clear
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {corrections.length === 0 ? (
        <Typography color="text.secondary">No corrections match the current filters.</Typography>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  checked={allSelected}
                  indeterminate={selectedIds.length > 0 && !allSelected}
                  onChange={toggleSelectAll}
                  disabled={pendingSelectable.length === 0}
                />
              </TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Original</TableCell>
              <TableCell>Corrected</TableCell>
              <TableCell>Language</TableCell>
              <TableCell>Domain</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Submitted</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {corrections.map((row) => (
              <TableRow key={row.id} hover>
                <TableCell padding="checkbox">
                  <Checkbox
                    checked={selectedIds.includes(row.id)}
                    onChange={() => toggleSelect(row.id)}
                    disabled={row.status !== "pending"}
                  />
                </TableCell>
                <TableCell>{row.correction_type}</TableCell>
                <TableCell sx={{ maxWidth: 220 }}>
                  <Typography variant="body2" noWrap title={row.original_value}>
                    {row.original_value}
                  </Typography>
                </TableCell>
                <TableCell sx={{ maxWidth: 220 }}>
                  <Typography variant="body2" noWrap title={row.corrected_value}>
                    {row.corrected_value}
                  </Typography>
                </TableCell>
                <TableCell>{row.source_language}</TableCell>
                <TableCell>{row.domain}</TableCell>
                <TableCell>
                  <Chip size="small" label={row.status} color={row.status === "pending" ? "warning" : "default"} />
                </TableCell>
                <TableCell>{formatTimestamp(row.submitted_at)}</TableCell>
                <TableCell>
                  <Button size="small" onClick={() => setDetailId(row.id)}>
                    Review
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Dialog open={Boolean(detailId)} onClose={() => setDetailId(null)} maxWidth="md" fullWidth>
        <DialogTitle>Correction review</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          {detail ? (
            <>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                <Chip label={detail.correction_type} />
                <Chip label={detail.source_language} variant="outlined" />
                <Chip label={detail.domain} variant="outlined" />
                <Chip label={detail.status} color={detail.status === "pending" ? "warning" : "default"} />
              </Box>

              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Pipeline context
                </Typography>
                <AuditContext audit={detail.audit_record} />
              </Box>

              <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
                <TextField label="Original value" value={detail.original_value} multiline minRows={2} InputProps={{ readOnly: true }} />
                <TextField
                  label="Corrected value"
                  value={editedValue}
                  onChange={(event) => setEditedValue(event.target.value)}
                  multiline
                  minRows={2}
                  disabled={detail.status !== "pending"}
                />
              </Box>

              {detail.correction_type === "glossary_addition" ? (
                <Alert severity="info">
                  Approving will upsert glossary entry: <strong>{detail.original_value}</strong> to{" "}
                  <strong>{editedValue || detail.corrected_value}</strong> in domain {detail.domain}.
                </Alert>
              ) : null}

              {detail.status === "pending" ? (
                <Box>
                  <Typography variant="body2" sx={{ mb: 0.5 }}>
                    Quality score
                  </Typography>
                  <Rating value={qualityScore} onChange={(_event, value) => setQualityScore(value)} />
                </Box>
              ) : null}

              {showReject ? (
                <TextField
                  label="Rejection reason"
                  value={rejectReason}
                  onChange={(event) => setRejectReason(event.target.value)}
                  multiline
                  minRows={2}
                  fullWidth
                />
              ) : null}
            </>
          ) : (
            <SkeletonDetailPanel fields={4} />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailId(null)}>Close</Button>
          {detail?.status === "pending" ? (
            <>
              {!showReject ? (
                <Button color="error" onClick={() => setShowReject(true)}>
                  Reject
                </Button>
              ) : (
                <Button color="error" disabled={working} onClick={() => void handleReject()}>
                  Confirm reject
                </Button>
              )}
              <Button variant="contained" disabled={working} onClick={() => void handleApprove()}>
                Approve
              </Button>
            </>
          ) : null}
        </DialogActions>
      </Dialog>
    </Box>
  );
}
