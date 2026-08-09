"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useRouter } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import {
  VOICE_LANGUAGE_OPTIONS,
  fetchVoiceTemplateCategories,
  uploadVoiceTemplate,
} from "@/lib/voice-templates-api";

const WORKSPACE_ID = "default";

export default function VoiceTemplateUploadPage() {
  const router = useRouter();
  const { data: categories = [] } = useSWR("voice-template-categories-upload", () => fetchVoiceTemplateCategories());
  const [categoryId, setCategoryId] = React.useState("greeting");
  const [languageCode, setLanguageCode] = React.useState("ak-GH");
  const [transcript, setTranscript] = React.useState("");
  const [transcriptEnglish, setTranscriptEnglish] = React.useState("");
  const [recordedBy, setRecordedBy] = React.useState("");
  const [recordedAt, setRecordedAt] = React.useState(() => new Date().toISOString().slice(0, 10));
  const [dialectNote, setDialectNote] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) {
      setError("Select a WAV file to upload.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const result = await uploadVoiceTemplate({
        file,
        category_id: categoryId,
        language_code: languageCode,
        transcript,
        transcript_english: transcriptEnglish,
        recorded_by: recordedBy,
        recorded_at: recordedAt,
        dialect_note: dialectNote || undefined,
        workspace_id: WORKSPACE_ID,
      });
      setMessage("Template submitted for review.");
      router.push(`/settings/voice-templates/${result.template_id}`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Upload failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Upload voice template"
        description="16 kHz, 16-bit mono WAV, 0.5 to 30 seconds. Recorded by a native speaker."
        actions={
          <Button component="a" href="/settings/voice-templates" size="small">
            Back to templates
          </Button>
        }
      />

      <Box component="form" onSubmit={handleSubmit} sx={{ display: "grid", gap: 2, maxWidth: 640 }}>
        <FormControl fullWidth>
          <InputLabel>Category</InputLabel>
          <Select label="Category" value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
            {categories.map((category) => (
              <MenuItem key={category.id} value={category.id}>
                {category.label} ({category.id})
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl fullWidth>
          <InputLabel>Language</InputLabel>
          <Select label="Language" value={languageCode} onChange={(event) => setLanguageCode(event.target.value)}>
            {VOICE_LANGUAGE_OPTIONS.map((lang) => (
              <MenuItem key={lang.code} value={lang.code}>
                {lang.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField
          label="Transcript (native language)"
          value={transcript}
          onChange={(event) => setTranscript(event.target.value)}
          required
          fullWidth
          multiline
          minRows={2}
        />
        <TextField
          label="English translation"
          value={transcriptEnglish}
          onChange={(event) => setTranscriptEnglish(event.target.value)}
          required
          fullWidth
          multiline
          minRows={2}
        />
        <TextField
          label="Recorded by"
          value={recordedBy}
          onChange={(event) => setRecordedBy(event.target.value)}
          required
          fullWidth
        />
        <TextField
          label="Recorded at"
          type="date"
          value={recordedAt}
          onChange={(event) => setRecordedAt(event.target.value)}
          required
          fullWidth
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Dialect note (optional)"
          value={dialectNote}
          onChange={(event) => setDialectNote(event.target.value)}
          fullWidth
          placeholder="e.g. Asante Twi"
        />

        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Audio file (WAV)
          </Typography>
          <input
            type="file"
            accept="audio/wav,.wav"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </Box>

        {error ? <Alert severity="error">{error}</Alert> : null}
        {message ? <Alert severity="success">{message}</Alert> : null}

        <Box sx={{ display: "flex", gap: 1 }}>
          <Button type="submit" variant="contained" disabled={submitting}>
            {submitting ? "Uploading..." : "Submit for review"}
          </Button>
          <Button component="a" href="/settings/voice-templates">
            Cancel
          </Button>
        </Box>
      </Box>
    </Box>
  );
}
