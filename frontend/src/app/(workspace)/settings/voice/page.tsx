"use client";

import MicIcon from "@mui/icons-material/Mic";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import SaveIcon from "@mui/icons-material/Save";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import Link from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList } from "@/components/ui/loading";
import { fetchVoiceSettings, saveVoiceSettings, type VoiceSettings } from "@/lib/audio-api";
import { docsPageUrl } from "@/lib/docs-url";

const DOCS_VOICE_INPUT = docsPageUrl("features/web-voice-input");

export default function VoiceSettingsPage() {
  const { data, error, isLoading, mutate } = useSWR("voice-settings", fetchVoiceSettings);
  const [message, setMessage] = React.useState<string | null>(null);
  const [messageSeverity, setMessageSeverity] = React.useState<"success" | "warning" | "error" | "info">("info");
  const [saving, setSaving] = React.useState(false);

  const [enabled, setEnabled] = React.useState(true);
  const [provider, setProvider] = React.useState("local");
  const [maxRecording, setMaxRecording] = React.useState(120);
  const [localModel, setLocalModel] = React.useState("base");
  const [localLanguage, setLocalLanguage] = React.useState("");
  const [openaiModel, setOpenaiModel] = React.useState("whisper-1");
  const [mistralModel, setMistralModel] = React.useState("voxtral-mini-latest");
  const [elevenlabsModel, setElevenlabsModel] = React.useState("scribe_v2");
  const [groqModel, setGroqModel] = React.useState("whisper-large-v3-turbo");
  const [geminiModel, setGeminiModel] = React.useState("gemini-2.5-flash");
  const [autoTts, setAutoTts] = React.useState(false);
  const [beepEnabled, setBeepEnabled] = React.useState(true);
  const [apiKey, setApiKey] = React.useState("");
  const [clearKey, setClearKey] = React.useState(false);
  const [keyFocused, setKeyFocused] = React.useState(false);

  const KEY_MASK = "••••••••••••••••••••";

  React.useEffect(() => {
    if (!data) return;
    applySnapshot(data);
  }, [data]);

  function applySnapshot(snapshot: VoiceSettings) {
    setEnabled(Boolean(snapshot.enabled));
    setProvider(snapshot.configured_provider || snapshot.configuredProvider || snapshot.provider || "local");
    setMaxRecording(snapshot.max_recording_seconds ?? snapshot.maxRecordingSeconds ?? 120);
    setLocalModel(snapshot.local_model ?? snapshot.localModel ?? "base");
    setLocalLanguage(snapshot.local_language ?? snapshot.localLanguage ?? "");
    setOpenaiModel(snapshot.openai_model ?? snapshot.openaiModel ?? "whisper-1");
    setMistralModel(snapshot.mistral_model ?? snapshot.mistralModel ?? "voxtral-mini-latest");
    setElevenlabsModel(snapshot.elevenlabs_model ?? snapshot.elevenlabsModel ?? "scribe_v2");
    setGroqModel(snapshot.groq_model ?? snapshot.groqModel ?? "whisper-large-v3-turbo");
    setGeminiModel(snapshot.gemini_model ?? (snapshot as { geminiModel?: string }).geminiModel ?? "gemini-2.5-flash");
    setAutoTts(snapshot.auto_tts ?? snapshot.autoTts ?? false);
    setBeepEnabled(snapshot.beep_enabled ?? snapshot.beepEnabled ?? true);
  }

  const activeCatalog = data?.catalog?.find((item) => item.id === provider);
  const needsKey = Boolean(activeCatalog?.needs_key);
  const hasKey = Boolean(activeCatalog?.has_api_key);
  const activeKeyUrl = activeCatalog?.key_url || activeCatalog?.keyUrl || null;
  const formRef = React.useRef<HTMLDivElement | null>(null);
  const showKeyMask = Boolean(needsKey && hasKey && !clearKey && !apiKey && !keyFocused);
  const apiKeyFieldValue = showKeyMask ? KEY_MASK : apiKey;

  async function persistSettings(overrides: Record<string, unknown> = {}) {
    setSaving(true);
    setMessage(null);
    try {
      const nextProvider = String(overrides.provider ?? provider);
      const catalogItem = data?.catalog?.find((item) => item.id === nextProvider);
      const payload: Record<string, unknown> = {
        enabled: overrides.enabled ?? enabled,
        provider: nextProvider,
        maxRecordingSeconds: maxRecording,
        localModel,
        localLanguage,
        openaiModel,
        mistralModel,
        elevenlabsModel,
        groqModel,
        geminiModel,
        autoTts,
        beepEnabled,
        ...overrides,
      };
      if (clearKey && nextProvider) {
        payload.clearApiKeyFor = nextProvider;
      } else if (
        apiKey.trim() &&
        apiKey !== KEY_MASK &&
        catalogItem?.needs_key &&
        catalogItem?.env_key
      ) {
        payload.apiKeys = { [catalogItem.env_key]: apiKey.trim() };
      }
      const saved = await saveVoiceSettings(payload);
      applySnapshot(saved);
      setApiKey("");
      setClearKey(false);
      setKeyFocused(false);
      await mutate(saved, { revalidate: false });
      return saved;
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Save failed");
      setMessageSeverity("error");
      throw err;
    } finally {
      setSaving(false);
    }
  }

  async function handleSave() {
    try {
      await persistSettings();
      setMessage("Voice settings saved. Chat mic uses these values immediately.");
      setMessageSeverity("success");
    } catch {
      // message already set
    }
  }

  async function activateProvider(providerId: string) {
    setProvider(providerId);
    setApiKey("");
    setClearKey(false);
    setKeyFocused(false);
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const saved = await persistSettings({ provider: providerId, enabled: true });
      const label = saved.catalog?.find((item) => item.id === providerId)?.label || providerId;
      const keyReady = saved.catalog?.find((item) => item.id === providerId)?.has_api_key;
      const needs = saved.catalog?.find((item) => item.id === providerId)?.needs_key;
      if (needs && !keyReady) {
        setMessage(`${label} is now active, but an API key is still needed. Paste it above and Save.`);
        setMessageSeverity("warning");
      } else {
        setMessage(`${label} is now the active speech-to-text provider.`);
        setMessageSeverity("success");
      }
    } catch {
      // message already set
    }
  }

  return (
    <Box>
      <PageHeader
        title="Voice input"
        description="Configure speech-to-text for chat dictation. Changes save to config and apply without editing YAML by hand."
        actions={
          <Stack direction="row" spacing={1}>
            <Button component={NextLink} href="/settings/voice-templates" variant="outlined" size="small">
              Voice templates
            </Button>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              disabled={saving || isLoading}
              onClick={() => void handleSave()}
            >
              Save
            </Button>
          </Stack>
        }
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error instanceof Error ? error.message : "Could not load voice settings"}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity={messageSeverity} sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      {isLoading || !data ? (
        <SkeletonList rows={5} rowHeight={72} />
      ) : (
        <Stack spacing={2}>
          <Card variant="outlined" ref={formRef}>
            <CardContent sx={{ display: "grid", gap: 2 }}>
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                <MicIcon fontSize="small" color="action" />
                <Typography variant="subtitle1">Speech-to-text</Typography>
                <Chip size="small" color={enabled ? "success" : "default"} label={enabled ? "Enabled" : "Disabled"} />
                {needsKey ? (
                  <Chip
                    size="small"
                    color={hasKey ? "success" : "warning"}
                    variant="outlined"
                    label={hasKey ? "API key saved" : "API key needed"}
                  />
                ) : (
                  <Chip size="small" variant="outlined" label="No API key required" />
                )}
              </Stack>

              <FormControlLabel
                control={<Switch checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />}
                label="Enable speech-to-text in workspace chat"
              />

              <TextField
                select
                label="Provider"
                value={provider}
                onChange={(e) => {
                  setProvider(e.target.value);
                  setApiKey("");
                  setClearKey(false);
                }}
                fullWidth
                helperText={activeCatalog?.description || "Provider used for /api/audio/transcribe"}
              >
                {(data.catalog || []).map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.label}
                    {item.badge ? ` (${item.badge})` : ""}
                  </MenuItem>
                ))}
              </TextField>

              <TextField
                label="Max recording (seconds)"
                type="number"
                value={maxRecording}
                onChange={(e) => setMaxRecording(Math.max(5, Math.min(600, Number(e.target.value) || 120)))}
                helperText="Browser push-to-talk stops at this limit (5-600)."
                fullWidth
              />

              {provider === "local" ? (
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  <TextField
                    select
                    label="Local model"
                    value={localModel}
                    onChange={(e) => setLocalModel(e.target.value)}
                    fullWidth
                  >
                    {(data.options?.local_models || ["tiny", "base", "small", "medium", "large-v3"]).map((model) => (
                      <MenuItem key={model} value={model}>
                        {model}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    label="Language (optional)"
                    value={localLanguage}
                    onChange={(e) => setLocalLanguage(e.target.value)}
                    placeholder="en, es, fr (blank = auto)"
                    fullWidth
                  />
                </Stack>
              ) : null}

              {provider === "openai" ? (
                <TextField select label="OpenAI model" value={openaiModel} onChange={(e) => setOpenaiModel(e.target.value)} fullWidth>
                  {(data.options?.openai_models || []).map((model) => (
                    <MenuItem key={model} value={model}>
                      {model}
                    </MenuItem>
                  ))}
                </TextField>
              ) : null}

              {provider === "mistral" ? (
                <TextField select label="Mistral model" value={mistralModel} onChange={(e) => setMistralModel(e.target.value)} fullWidth>
                  {(data.options?.mistral_models || []).map((model) => (
                    <MenuItem key={model} value={model}>
                      {model}
                    </MenuItem>
                  ))}
                </TextField>
              ) : null}

              {provider === "elevenlabs" ? (
                <TextField
                  select
                  label="ElevenLabs model"
                  value={elevenlabsModel}
                  onChange={(e) => setElevenlabsModel(e.target.value)}
                  fullWidth
                >
                  {(data.options?.elevenlabs_models || []).map((model) => (
                    <MenuItem key={model} value={model}>
                      {model}
                    </MenuItem>
                  ))}
                </TextField>
              ) : null}

              {provider === "groq" ? (
                <TextField select label="Groq model" value={groqModel} onChange={(e) => setGroqModel(e.target.value)} fullWidth>
                  {(data.options?.groq_models || []).map((model) => (
                    <MenuItem key={model} value={model}>
                      {model}
                    </MenuItem>
                  ))}
                </TextField>
              ) : null}

              {provider === "gemini" ? (
                <TextField
                  select
                  label="Gemini model"
                  value={geminiModel}
                  onChange={(e) => setGeminiModel(e.target.value)}
                  fullWidth
                  helperText="Uses multimodal audio understanding for transcription."
                >
                  {(data.options?.gemini_models || ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]).map(
                    (model) => (
                      <MenuItem key={model} value={model}>
                        {model}
                      </MenuItem>
                    ),
                  )}
                </TextField>
              ) : null}

              {needsKey ? (
                <>
                  <TextField
                    label={`API key${activeCatalog?.env_key ? ` (${activeCatalog.env_key})` : ""}`}
                    type="password"
                    value={clearKey ? "" : apiKeyFieldValue}
                    onFocus={() => {
                      setKeyFocused(true);
                      if (showKeyMask) setApiKey("");
                    }}
                    onBlur={() => setKeyFocused(false)}
                    onChange={(e) => {
                      const next = e.target.value;
                      if (next === KEY_MASK) return;
                      setApiKey(next);
                      if (clearKey && next.trim()) setClearKey(false);
                    }}
                    placeholder={hasKey && !clearKey ? KEY_MASK : "Paste API key"}
                    disabled={clearKey}
                    fullWidth
                    InputLabelProps={{ shrink: true }}
                    helperText={
                      clearKey ? (
                        "Saved key will be removed on Save."
                      ) : hasKey && !apiKey ? (
                        <>
                          Saved key is on file (shown redacted). Paste a new key to replace it.
                          {activeKeyUrl ? (
                            <>
                              {" "}
                              <Link href={activeKeyUrl} target="_blank" rel="noopener noreferrer">
                                Get an API key here
                              </Link>
                            </>
                          ) : null}
                        </>
                      ) : activeKeyUrl ? (
                        <>
                          Need a key?{" "}
                          <Link href={activeKeyUrl} target="_blank" rel="noopener noreferrer">
                            Get an API key here
                          </Link>
                        </>
                      ) : (
                        "Paste the provider API key, then Save."
                      )
                    }
                  />
                  {activeKeyUrl ? (
                    <Button
                      component="a"
                      href={activeKeyUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      size="small"
                      variant="outlined"
                      startIcon={<OpenInNewIcon fontSize="small" />}
                      sx={{ justifySelf: "start" }}
                    >
                      Open {activeCatalog?.label || "provider"} API key page
                    </Button>
                  ) : null}
                  <FormControlLabel
                    control={
                      <Switch
                        checked={clearKey}
                        onChange={(e) => {
                          setClearKey(e.target.checked);
                          if (e.target.checked) {
                            setApiKey("");
                            setKeyFocused(false);
                          }
                        }}
                      />
                    }
                    label="Clear saved API key on save"
                  />
                </>
              ) : null}

              <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                <FormControlLabel
                  control={<Switch checked={beepEnabled} onChange={(e) => setBeepEnabled(e.target.checked)} />}
                  label="CLI record beeps"
                />
                <FormControlLabel
                  control={<Switch checked={autoTts} onChange={(e) => setAutoTts(e.target.checked)} />}
                  label="CLI auto-TTS replies"
                />
              </Stack>

              <Typography variant="caption" color="text.secondary">
                Transcribe endpoint: {data.transcribe_path || "/api/audio/transcribe"}
              </Typography>
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent sx={{ display: "grid", gap: 1 }}>
              <Typography variant="subtitle2">Providers</Typography>
              <Box
                sx={{
                  display: { xs: "none", sm: "grid" },
                  gridTemplateColumns: "minmax(160px, 1.4fr) 88px 104px 88px 88px",
                  columnGap: 1.5,
                  px: 1.5,
                  pb: 0.5,
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  Provider
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Tier
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  API key
                </Typography>
                <Typography variant="caption" color="text.secondary" />
                <Typography variant="caption" color="text.secondary" sx={{ textAlign: "right" }}>
                  Action
                </Typography>
              </Box>
              <Stack spacing={0.75}>
                {(data.catalog || []).map((item) => {
                  const keyUrl = item.key_url || item.keyUrl || null;
                  const keyLabel = !item.needs_key
                    ? "Not required"
                    : item.has_api_key
                      ? "Ready"
                      : "Missing";
                  const keyColor = !item.needs_key
                    ? "text.secondary"
                    : item.has_api_key
                      ? "success.main"
                      : "warning.main";
                  return (
                    <Box
                      key={item.id}
                      sx={{
                        display: "grid",
                        gridTemplateColumns: {
                          xs: "1fr auto",
                          sm: "minmax(160px, 1.4fr) 88px 104px 88px 88px",
                        },
                        columnGap: 1.5,
                        rowGap: 0.75,
                        alignItems: "center",
                        px: 1.5,
                        py: 1,
                        borderRadius: 1,
                        border: "1px solid",
                        borderColor: item.is_active ? "success.main" : "divider",
                        bgcolor: item.is_active ? "action.selected" : "transparent",
                      }}
                    >
                      <Box sx={{ minWidth: 0 }}>
                        <Typography variant="body2" fontWeight={600} noWrap>
                          {item.label}
                        </Typography>
                        {item.is_active ? (
                          <Typography variant="caption" color="success.main">
                            Active now
                          </Typography>
                        ) : null}
                      </Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ display: { xs: "none", sm: "block" } }}
                      >
                        {item.badge || ";"}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{ color: keyColor, display: { xs: "none", sm: "block" } }}
                      >
                        {keyLabel}
                      </Typography>
                      <Box
                        sx={{
                          display: { xs: "none", sm: "flex" },
                          justifyContent: "flex-start",
                        }}
                      >
                        {keyUrl && item.needs_key ? (
                          <Button
                            component="a"
                            href={keyUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            size="small"
                            startIcon={<OpenInNewIcon fontSize="small" />}
                            sx={{ px: 0.5, minWidth: 0 }}
                          >
                            Get key
                          </Button>
                        ) : (
                          <Typography variant="caption" color="text.disabled">
;
                          </Typography>
                        )}
                      </Box>
                      <Box sx={{ display: "flex", justifyContent: "flex-end", gridColumn: { xs: "2", sm: "auto" } }}>
                        <Button
                          size="small"
                          variant={item.is_active ? "outlined" : "contained"}
                          disabled={saving || Boolean(item.is_active)}
                          onClick={() => void activateProvider(item.id)}
                          sx={{ minWidth: 72 }}
                        >
                          {item.is_active ? "Active" : "Use"}
                        </Button>
                      </Box>
                      <Stack
                        direction="row"
                        spacing={1}
                        alignItems="center"
                        sx={{ display: { xs: "flex", sm: "none" }, gridColumn: "1 / -1" }}
                      >
                        {item.badge ? (
                          <Typography variant="caption" color="text.secondary">
                            {item.badge}
                          </Typography>
                        ) : null}
                        <Typography variant="caption" sx={{ color: keyColor }}>
                          {keyLabel}
                        </Typography>
                        {keyUrl && item.needs_key ? (
                          <Button
                            component="a"
                            href={keyUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            size="small"
                            sx={{ px: 0.5, minWidth: 0 }}
                          >
                            Get key
                          </Button>
                        ) : null}
                      </Stack>
                    </Box>
                  );
                })}
              </Stack>
            </CardContent>
          </Card>

          <Alert severity="info">
            Use the microphone in workspace chat to dictate, review the transcript, then Send. See{" "}
            <Link href={DOCS_VOICE_INPUT} target="_blank" rel="noopener noreferrer">
              web voice input docs
            </Link>
            .
          </Alert>
        </Stack>
      )}
    </Box>
  );
}
