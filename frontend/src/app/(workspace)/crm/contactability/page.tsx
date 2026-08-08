"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { fetchCrmContactability, upsertCrmContactability } from "@/lib/crm-api";

export default function CrmContactabilityPage() {
  const [subjectId, setSubjectId] = React.useState("");
  const [subjectType, setSubjectType] = React.useState("lead");
  const [decision, setDecision] = React.useState("allow");
  const [reason, setReason] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const list = useSWR(["crm-contactability", CRM_WORKSPACE], () => fetchCrmContactability(CRM_WORKSPACE));

  const save = async () => {
    setError(null);
    try {
      await upsertCrmContactability(
        {
          subject_type: subjectType,
          subject_id: subjectId,
          channel: "email",
          purpose: "cold_outreach",
          decision,
          reason,
        },
        CRM_WORKSPACE,
      );
      setSubjectId("");
      await list.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  };

  return (
    <Stack spacing={2} sx={{ maxWidth: 720 }}>
      <Typography variant="body2" color="text.secondary">
        Per-person allow / deny / needs_review. Discovery hits are not contact permission.
      </Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel id="st">Type</InputLabel>
          <Select labelId="st" label="Type" value={subjectType} onChange={(e) => setSubjectType(String(e.target.value))}>
            <MenuItem value="lead">Lead</MenuItem>
            <MenuItem value="contact">Contact</MenuItem>
          </Select>
        </FormControl>
        <TextField size="small" fullWidth label="Subject id" value={subjectId} onChange={(e) => setSubjectId(e.target.value)} />
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel id="dec">Decision</InputLabel>
          <Select labelId="dec" label="Decision" value={decision} onChange={(e) => setDecision(String(e.target.value))}>
            <MenuItem value="allow">Allow</MenuItem>
            <MenuItem value="deny">Deny</MenuItem>
            <MenuItem value="needs_review">Needs review</MenuItem>
          </Select>
        </FormControl>
        <Button variant="contained" onClick={() => void save()}>
          Save
        </Button>
      </Stack>
      <TextField size="small" label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} />
      {(list.data?.items || []).map((row) => (
        <Typography key={String(row.id)} variant="body2" color="text.secondary">
          {String(row.subject_type)}/{String(row.subject_id)} · {String(row.decision)} · {String(row.reason || "")}
        </Typography>
      ))}
    </Stack>
  );
}
