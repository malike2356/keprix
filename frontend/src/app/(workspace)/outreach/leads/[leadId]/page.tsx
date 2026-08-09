"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import { PIPELINE_STAGES, pipelineLabel } from "@/components/outreach/types";
import {
  enrollOutreachLead,
  fetchOutreachLead,
  fetchOutreachSequences,
  patchOutreachLead,
} from "@/lib/outreach-api";

const WORKSPACE = "default";

export default function OutreachLeadDetailPage() {
  const params = useParams<{ leadId: string }>();
  const leadId = params.leadId;
  const [sequenceId, setSequenceId] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const detail = useSWR(leadId ? ["outreach-lead", WORKSPACE, leadId] : null, () =>
    fetchOutreachLead(leadId, WORKSPACE),
  );
  const sequences = useSWR(["outreach-sequences", WORKSPACE], () => fetchOutreachSequences(WORKSPACE));

  React.useEffect(() => {
    const first = sequences.data?.sequences?.[0]?.id;
    if (!sequenceId && first) setSequenceId(first);
  }, [sequences.data, sequenceId]);

  const lead = detail.data?.lead;

  const onEnroll = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!sequenceId) throw new Error("No sequence available");
      await enrollOutreachLead(
        {
          lead_id: leadId,
          sequence_id: sequenceId,
          campaign_id: lead?.campaign_id || lead?.campaignId || undefined,
        },
        WORKSPACE,
      );
      setMessage("Lead enrolled in sequence");
      await detail.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not enroll lead");
    } finally {
      setBusy(false);
    }
  };

  const onStatus = async (status: string) => {
    setBusy(true);
    setError(null);
    try {
      await patchOutreachLead(leadId, { status }, WORKSPACE);
      setMessage(`Status set to ${pipelineLabel(status)}`);
      await detail.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update status");
    } finally {
      setBusy(false);
    }
  };

  if (detail.isLoading && !detail.data) {
    return <Typography color="text.secondary">Loading lead...</Typography>;
  }

  if (!lead) {
    return (
      <Typography color="text.secondary">
        Lead not found.{" "}
        <Typography component="a" href="/outreach/leads" color="primary" sx={{ textDecoration: "underline" }}>
          Back
        </Typography>
      </Typography>
    );
  }

  return (
    <Stack spacing={2} sx={{ maxWidth: 720 }}>
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

      <Button size="small" component="a" href="/outreach/leads" sx={{ alignSelf: "flex-start" }}>
        All leads
      </Button>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="h5">{lead.name}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {pipelineLabel(lead.status)}
            {lead.email ? ` · ${lead.email}` : ""}
            {lead.company ? ` · ${lead.company}` : ""}
            {lead.phone ? ` · ${lead.phone}` : ""}
          </Typography>
          {lead.notes ? (
            <Typography variant="body2" sx={{ mt: 2 }}>
              {lead.notes}
            </Typography>
          ) : null}
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Enroll in sequence
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }}>
            <FormControl size="small" fullWidth>
              <InputLabel id="lead-seq">Sequence</InputLabel>
              <Select
                labelId="lead-seq"
                label="Sequence"
                value={sequenceId}
                onChange={(e) => setSequenceId(e.target.value)}
              >
                {(sequences.data?.sequences ?? []).map((seq) => (
                  <MenuItem key={seq.id} value={seq.id}>
                    {seq.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button size="small" variant="contained" disabled={busy} onClick={() => void onEnroll()}>
              Enroll
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Update status
          </Typography>
          <FormControl size="small" fullWidth sx={{ mb: 1.5 }}>
            <InputLabel id="lead-status">Status</InputLabel>
            <Select
              labelId="lead-status"
              label="Status"
              value={lead.status}
              disabled={busy}
              onChange={(e) => void onStatus(e.target.value)}
            >
              {PIPELINE_STAGES.map((stage) => (
                <MenuItem key={stage} value={stage}>
                  {pipelineLabel(stage)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button size="small" variant="outlined" disabled={busy} onClick={() => void onStatus("replied")}>
              Mark replied
            </Button>
            <Button size="small" variant="outlined" disabled={busy} onClick={() => void onStatus("booked")}>
              Mark booked
            </Button>
            <Button size="small" variant="outlined" disabled={busy} onClick={() => void onStatus("unsubscribed")}>
              Unsubscribe
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {(lead.timeline ?? []).length > 0 ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>
              Timeline
            </Typography>
            <Stack spacing={1}>
              {(lead.timeline ?? []).map((event, index) => (
                <Typography key={event.id || index} variant="body2" color="text.secondary">
                  {event.at ? `${new Date(event.at).toLocaleString()} · ` : ""}
                  {event.message || event.kind || "Event"}
                </Typography>
              ))}
            </Stack>
          </CardContent>
        </Card>
      ) : null}
    </Stack>
  );
}
