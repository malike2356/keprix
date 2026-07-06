"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Rating from "@mui/material/Rating";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import { useCESession } from "@/lib/ce-auth";
import {
  approveVoiceTemplate,
  archiveVoiceTemplate,
  fetchVoiceTemplate,
  rejectVoiceTemplate,
  voiceTemplateAudioUrl,
} from "@/lib/voice-templates-api";

export default function VoiceTemplateDetailPage() {
  const params = useParams<{ id: string }>();
  const templateId = params.id;
  const router = useRouter();
  const { user } = useCESession();
  const isAdmin = user?.role === "admin" || user?.role === "owner";
  const { data: template, mutate } = useSWR(templateId ? `voice-template-${templateId}` : null, () =>
    fetchVoiceTemplate(templateId),
  );

  const [qualityRating, setQualityRating] = React.useState<number | null>(4);
  const [rejectReason, setRejectReason] = React.useState("");
  const [showReject, setShowReject] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [working, setWorking] = React.useState(false);

  if (!template) {
    return (
      <Box>
        <PageHeader title="Voice template" description="Review uploaded voice template details." />
        <SkeletonDetailPanel fields={5} />
      </Box>
    );
  }

  const audioSrc = voiceTemplateAudioUrl(template.audio_url);

  const handleApprove = async () => {
    if (!qualityRating) {
      setError("Select a quality rating before approving.");
      return;
    }
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      await approveVoiceTemplate(templateId, qualityRating);
      await mutate();
      setMessage("Template approved.");
    } catch (approveError) {
      setError(approveError instanceof Error ? approveError.message : "Approve failed");
    } finally {
      setWorking(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      setError("Enter a rejection reason.");
      return;
    }
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      await rejectVoiceTemplate(templateId, rejectReason.trim());
      await mutate();
      setMessage("Template rejected.");
      setShowReject(false);
    } catch (rejectError) {
      setError(rejectError instanceof Error ? rejectError.message : "Reject failed");
    } finally {
      setWorking(false);
    }
  };

  const handleArchive = async () => {
    setWorking(true);
    setError(null);
    try {
      await archiveVoiceTemplate(templateId);
      router.push("/settings/voice-templates");
    } catch (archiveError) {
      setError(archiveError instanceof Error ? archiveError.message : "Archive failed");
    } finally {
      setWorking(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Voice template review"
        description={`${template.category_id} · ${template.language_code}`}
        actions={
          <Button component={Link} href="/settings/voice-templates" size="small">
            Back to templates
          </Button>
        }
      />

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary">
            Status: {template.status}
          </Typography>
          <Typography variant="body1" sx={{ mt: 1 }}>
            {template.transcript}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {template.transcript_english}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>
            Recorded by {template.recorded_by || "unknown"} on {template.recorded_at || "unknown"} ·{" "}
            {template.duration_seconds.toFixed(1)}s · plays {template.play_count}
          </Typography>
          {template.dialect_note ? (
            <Typography variant="caption" color="text.secondary" display="block">
              Dialect: {template.dialect_note}
            </Typography>
          ) : null}
          {audioSrc ? (
            <Box component="audio" controls src={audioSrc} sx={{ mt: 2, width: "100%" }} />
          ) : null}
        </CardContent>
      </Card>

      {template.rejection_reason ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Rejection reason: {template.rejection_reason}
        </Alert>
      ) : null}

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }}>
          {message}
        </Alert>
      ) : null}

      {isAdmin ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Review actions
            </Typography>
            {template.status === "pending" ? (
              <Box sx={{ display: "grid", gap: 2 }}>
                <Box>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    Quality rating
                  </Typography>
                  <Rating
                    value={qualityRating}
                    onChange={(_event, value) => setQualityRating(value)}
                    max={5}
                  />
                </Box>
                <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                  <Button variant="contained" onClick={handleApprove} disabled={working}>
                    Approve
                  </Button>
                  <Button variant="outlined" color="warning" onClick={() => setShowReject((value) => !value)} disabled={working}>
                    Reject
                  </Button>
                </Box>
                {showReject ? (
                  <Box sx={{ display: "grid", gap: 1 }}>
                    <TextField
                      label="Rejection reason"
                      value={rejectReason}
                      onChange={(event) => setRejectReason(event.target.value)}
                      fullWidth
                      multiline
                      minRows={2}
                    />
                    <Button color="warning" variant="contained" onClick={handleReject} disabled={working}>
                      Confirm reject
                    </Button>
                  </Box>
                ) : null}
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                This template is {template.status}.
              </Typography>
            )}
            {template.status === "approved" ? (
              <Button color="inherit" onClick={handleArchive} disabled={working}>
                Archive template
              </Button>
            ) : null}
          </CardContent>
        </Card>
      ) : (
        <Alert severity="info">Admin access is required to approve or reject templates.</Alert>
      )}
    </Box>
  );
}
