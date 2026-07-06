"use client";

import MicIcon from "@mui/icons-material/Mic";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList } from "@/components/ui/loading";
import { fetchAudioStatus } from "@/lib/audio-api";
import { docsPageUrl } from "@/lib/docs-url";

const DOCS_ENV_VARS = docsPageUrl("configuration/environment-variables");
const DOCS_VOICE_INPUT = docsPageUrl("features/web-voice-input");

export default function VoiceSettingsPage() {
  const { data, error, isLoading } = useSWR("audio-status", fetchAudioStatus);

  return (
    <Box>
      <PageHeader
        title="Voice input"
        description="Speech-to-text status for chat dictation. Configuration is read-only in the workspace UI."
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error instanceof Error ? error.message : "Could not load speech-to-text status"}
        </Alert>
      ) : null}

      {isLoading ? (
        <SkeletonList rows={3} rowHeight={72} />
      ) : (
        <Stack spacing={2}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
                <MicIcon fontSize="small" color="action" />
                <Typography variant="subtitle1">Speech-to-text</Typography>
                <Chip
                  size="small"
                  color={data?.stt_enabled ? "success" : "default"}
                  label={data?.stt_enabled ? "Enabled" : "Disabled"}
                />
              </Stack>
              <Stack spacing={1}>
                <Typography variant="body2">
                  <strong>Provider:</strong> {data?.provider || "not configured"}
                </Typography>
                <Typography variant="body2">
                  <strong>Max recording:</strong> {data?.max_recording_seconds ?? 120} seconds
                </Typography>
                <Typography variant="body2">
                  <strong>Transcribe endpoint:</strong> {data?.transcribe_path || "/api/audio/transcribe"}
                </Typography>
              </Stack>
            </CardContent>
          </Card>

          <Alert severity="info">
            STT is configured in Keprix <code>config.yaml</code> under <code>stt</code> and{" "}
            <code>voice.max_recording_seconds</code>. This page does not edit runtime behaviour.
          </Alert>

          <Typography variant="body2" color="text.secondary">
            Cloud providers (Groq, OpenAI, Mistral, and others) require API keys documented in{" "}
            <Link href={DOCS_ENV_VARS} target="_blank" rel="noopener noreferrer">
              environment variables
            </Link>
            . Local transcription uses faster-whisper on the server.
          </Typography>

          <Typography variant="body2" color="text.secondary">
            Use the microphone in workspace chat to dictate a message, review the transcript, then Send. See{" "}
            <Link href={DOCS_VOICE_INPUT} target="_blank" rel="noopener noreferrer">
              web voice input
            </Link>{" "}
            for troubleshooting and browser requirements.
          </Typography>
        </Stack>
      )}
    </Box>
  );
}
