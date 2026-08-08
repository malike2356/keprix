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
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import { fetchCrmContactability, upsertCrmContactability } from "@/lib/crm-api";

const WORKSPACE = "default";

export default function OutreachContactabilityPage() {
  const { data, error, mutate, isLoading } = useSWR(["crm-contactability", WORKSPACE], () =>
    fetchCrmContactability(WORKSPACE),
  );
  const [subjectType, setSubjectType] = React.useState("lead");
  const [subjectId, setSubjectId] = React.useState("");
  const [channel, setChannel] = React.useState("email");
  const [purpose, setPurpose] = React.useState("outreach");
  const [jurisdiction, setJurisdiction] = React.useState("UK");
  const [decision, setDecision] = React.useState("needs_review");
  const [reason, setReason] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg] = React.useState<string | null>(null);
  const [err, setErr] = React.useState<string | null>(null);

  const items = data?.items ?? [];
  const needsReview = items.filter((i) => String(i.decision) === "needs_review");

  const save = async () => {
    if (!subjectId.trim()) {
      setErr("Subject ID is required");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      await upsertCrmContactability(
        {
          subject_type: subjectType,
          subject_id: subjectId.trim(),
          channel,
          purpose,
          jurisdiction,
          decision,
          reason: reason.trim() || undefined,
          policy_version: "v1",
        },
        WORKSPACE,
      );
      setMsg("Contactability decision saved. Discovery success alone does not imply contactable.");
      await mutate();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

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

      <Typography variant="body2" color="text.secondary">
        Found is not contactable. Person x channel x purpose decisions gate enroll. Deny blocks Soft Wall enroll
        with a reason. See also{" "}
        <Button component={NextLink} href="/outreach/suppressions" size="small">
          Suppressions
        </Button>
        .
      </Typography>

      {needsReview.length > 0 ? (
        <Alert severity="warning">{needsReview.length} decision(s) need Soft Wall review.</Alert>
      ) : null}

      <Paper variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Subject</TableCell>
              <TableCell>Channel</TableCell>
              <TableCell>Purpose</TableCell>
              <TableCell>Jurisdiction</TableCell>
              <TableCell>Decision</TableCell>
              <TableCell>Policy</TableCell>
              <TableCell>Reason</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!isLoading && items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7}>
                  <EmptyState
                    title="No contactability decisions"
                    description="Discovery hits do not auto-allow contact. Add allow/deny/needs_review explicitly."
                  />
                </TableCell>
              </TableRow>
            ) : (
              items.map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell>
                    {String(row.subject_type)}/{String(row.subject_id)}
                  </TableCell>
                  <TableCell>{String(row.channel)}</TableCell>
                  <TableCell>{String(row.purpose)}</TableCell>
                  <TableCell>{String(row.jurisdiction)}</TableCell>
                  <TableCell>{String(row.decision)}</TableCell>
                  <TableCell>{String(row.policy_version || "")}</TableCell>
                  <TableCell>{String(row.reason || "")}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Upsert decision
        </Typography>
        <Stack spacing={1}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel id="st">Subject type</InputLabel>
              <Select labelId="st" label="Subject type" value={subjectType} onChange={(e) => setSubjectType(String(e.target.value))}>
                {["lead", "contact", "account"].map((t) => (
                  <MenuItem key={t} value={t}>
                    {t}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField size="small" label="Subject ID" value={subjectId} onChange={(e) => setSubjectId(e.target.value)} sx={{ flex: 1 }} />
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel id="ch">Channel</InputLabel>
              <Select labelId="ch" label="Channel" value={channel} onChange={(e) => setChannel(String(e.target.value))}>
                {["email", "phone", "telegram"].map((c) => (
                  <MenuItem key={c} value={c}>
                    {c}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <TextField size="small" label="Purpose" value={purpose} onChange={(e) => setPurpose(e.target.value)} />
            <TextField size="small" label="Jurisdiction" value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} />
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="dec">Decision</InputLabel>
              <Select labelId="dec" label="Decision" value={decision} onChange={(e) => setDecision(String(e.target.value))}>
                {["allow", "deny", "needs_review"].map((d) => (
                  <MenuItem key={d} value={d}>
                    {d}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
          <TextField size="small" label="Reason / evidence" value={reason} onChange={(e) => setReason(e.target.value)} fullWidth />
          <Button variant="contained" disabled={busy} onClick={() => void save()}>
            Save decision
          </Button>
        </Stack>
      </Paper>
    </Stack>
  );
}
