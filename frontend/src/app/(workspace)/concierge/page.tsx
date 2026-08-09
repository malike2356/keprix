"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import {
  fetchConciergeProfile,
  fetchPreview,
  fetchReadiness,
  publishConcierge,
  saveStep1,
  saveStep2,
  unpublishConcierge,
  type ConciergeProfile,
  type Readiness,
} from "@/lib/concierge-api";

const TABS = [
  "Setup",
  "Conversations",
  "Bookings",
  "Knowledge",
  "Channels",
  "Integrations",
  "Analytics",
] as const;

const DEFAULT_HOURS = {
  timezone: "Europe/London",
  windows: [
    { dayOfWeek: 1, start: "09:00", end: "17:00" },
    { dayOfWeek: 2, start: "09:00", end: "17:00" },
    { dayOfWeek: 3, start: "09:00", end: "17:00" },
    { dayOfWeek: 4, start: "09:00", end: "17:00" },
    { dayOfWeek: 5, start: "09:00", end: "17:00" },
  ],
};

export default function ConciergePage() {
  const [tab, setTab] = React.useState(0);
  const [step, setStep] = React.useState(1);
  const [personaId, setPersonaId] = React.useState("default");
  const [personaName, setPersonaName] = React.useState("");
  const [greeting, setGreeting] = React.useState("Hi, how can I help you today?");
  const [businessName, setBusinessName] = React.useState("");
  const [businessDescription, setBusinessDescription] = React.useState("");
  const [escalationEmail, setEscalationEmail] = React.useState("");
  const [knowledgeIds, setKnowledgeIds] = React.useState("");
  const [webEnabled, setWebEnabled] = React.useState(true);
  const [telegramEnabled, setTelegramEnabled] = React.useState(false);
  const [whatsappEnabled, setWhatsappEnabled] = React.useState(false);
  const [emailEnabled, setEmailEnabled] = React.useState(false);
  const [calendarProvider, setCalendarProvider] = React.useState("");
  const [conferencingProvider, setConferencingProvider] = React.useState("");
  const [meetingName, setMeetingName] = React.useState("");
  const [meetingMinutes, setMeetingMinutes] = React.useState(30);
  const [profile, setProfile] = React.useState<ConciergeProfile | null>(null);
  const [readiness, setReadiness] = React.useState<Readiness | null>(null);
  const [previewGreeting, setPreviewGreeting] = React.useState<string | null>(null);
  const [embedUrl, setEmbedUrl] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const load = React.useCallback(async () => {
    setError(null);
    try {
      const [{ profile: p }, ready, preview] = await Promise.all([
        fetchConciergeProfile(personaId),
        fetchReadiness(personaId),
        fetchPreview(personaId),
      ]);
      setProfile(p);
      setReadiness(ready);
      setPreviewGreeting(preview.visitorView.greeting);
      setEmbedUrl(preview.visitorView.publicUrl || null);
      if (p) {
        setPersonaName(p.personaName || "");
        setGreeting(p.greetingMessage || "");
        setBusinessName(p.businessName || "");
        setBusinessDescription(p.businessDescription || "");
        setEscalationEmail(p.escalationEmail || "");
        setKnowledgeIds((p.knowledgeSourceIds || []).join(", "));
        const ch = p.channelConfig || {};
        setWebEnabled(Boolean((ch.web as { enabled?: boolean } | undefined)?.enabled));
        setTelegramEnabled(Boolean((ch.telegram as { enabled?: boolean } | undefined)?.enabled));
        setWhatsappEnabled(Boolean((ch.whatsapp as { enabled?: boolean } | undefined)?.enabled));
        setEmailEnabled(Boolean((ch.email as { enabled?: boolean } | undefined)?.enabled));
        setCalendarProvider(p.calendarProvider || "");
        setConferencingProvider(p.conferencingProvider || "");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Load failed");
    }
  }, [personaId]);

  React.useEffect(() => {
    void load();
  }, [load]);

  const onSaveStep1 = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await saveStep1({
        personaId,
        personaName,
        greetingMessage: greeting,
        businessName,
        businessDescription,
        escalationEmail,
        knowledgeSourceIds: knowledgeIds
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      setProfile(result.profile);
      setStep(2);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Step 1 failed");
    } finally {
      setBusy(false);
    }
  };

  const onSaveStep2 = async () => {
    setBusy(true);
    setError(null);
    try {
      const meetingTypes = meetingName.trim()
        ? [{ name: meetingName.trim(), durationMinutes: meetingMinutes, description: "" }]
        : [];
      const result = await saveStep2({
        personaId,
        channels: {
          web: { enabled: webEnabled },
          telegram: { enabled: telegramEnabled },
          whatsapp: { enabled: whatsappEnabled },
          email: { enabled: emailEnabled },
        },
        businessHours: DEFAULT_HOURS,
        calendarProvider: calendarProvider || null,
        conferencingProvider: conferencingProvider || null,
        calendarConnected: false,
        conferencingConnected: false,
        meetingTypes,
        icsFallbackOk: true,
      });
      setProfile(result.profile);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Step 2 failed");
    } finally {
      setBusy(false);
    }
  };

  const onPublish = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await publishConcierge(personaId);
      setProfile(result.profile);
      setEmbedUrl(result.widget.publicUrl);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Publish failed");
    } finally {
      setBusy(false);
    }
  };

  const onUnpublish = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await unpublishConcierge(personaId);
      setProfile(result.profile);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unpublish failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Customer Concierge"
        description="Publish a customer-facing concierge for your workspace. Visitors never receive a workspace-member session."
      />

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }} variant="scrollable">
        {TABS.map((label) => (
          <Tab key={label} label={label} />
        ))}
      </Tabs>

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      {tab === 0 ? (
        <Stack spacing={2} maxWidth={720}>
          <Typography variant="subtitle1">
            Setup wizard (step {step} of 2)
            {profile?.published ? " · Live" : " · Draft"}
          </Typography>

          <TextField
            label="Persona / binding id"
            value={personaId}
            onChange={(e) => setPersonaId(e.target.value)}
            helperText="One concierge profile per persona or workspace binding"
            fullWidth
          />

          {step === 1 ? (
            <>
              <TextField label="Persona name" value={personaName} onChange={(e) => setPersonaName(e.target.value)} fullWidth />
              <TextField label="Greeting" value={greeting} onChange={(e) => setGreeting(e.target.value)} fullWidth multiline minRows={2} />
              <TextField label="Business name" value={businessName} onChange={(e) => setBusinessName(e.target.value)} fullWidth />
              <TextField
                label="Business description"
                value={businessDescription}
                onChange={(e) => setBusinessDescription(e.target.value)}
                fullWidth
                multiline
                minRows={3}
              />
              <TextField
                label="Escalation email"
                value={escalationEmail}
                onChange={(e) => setEscalationEmail(e.target.value)}
                fullWidth
              />
              <TextField
                label="Knowledge source IDs (comma-separated)"
                value={knowledgeIds}
                onChange={(e) => setKnowledgeIds(e.target.value)}
                helperText="Published knowledge only; full enforcement lands in later prompts"
                fullWidth
              />
              <Button variant="contained" disabled={busy} onClick={() => void onSaveStep1()}>
                Save and continue
              </Button>
            </>
          ) : (
            <>
              <FormControlLabel control={<Checkbox checked={webEnabled} onChange={(e) => setWebEnabled(e.target.checked)} />} label="Web embed" />
              <FormControlLabel control={<Checkbox checked={telegramEnabled} onChange={(e) => setTelegramEnabled(e.target.checked)} />} label="Telegram" />
              <FormControlLabel control={<Checkbox checked={whatsappEnabled} onChange={(e) => setWhatsappEnabled(e.target.checked)} />} label="WhatsApp" />
              <FormControlLabel control={<Checkbox checked={emailEnabled} onChange={(e) => setEmailEnabled(e.target.checked)} />} label="Email" />
              <TextField
                select
                label="Calendar provider (optional)"
                value={calendarProvider}
                onChange={(e) => setCalendarProvider(e.target.value)}
                fullWidth
                helperText={calendarProvider ? "Connect in Integrations; not connected yet" : "ICS-only fallback available for Community Edition"}
              >
                <MenuItem value="">None (ICS fallback)</MenuItem>
                <MenuItem value="google">Google</MenuItem>
                <MenuItem value="microsoft">Microsoft</MenuItem>
                <MenuItem value="caldav">CalDAV</MenuItem>
              </TextField>
              <TextField
                select
                label="Conferencing provider (optional)"
                value={conferencingProvider}
                onChange={(e) => setConferencingProvider(e.target.value)}
                fullWidth
                helperText={conferencingProvider ? "Connect in Integrations; not connected yet" : "Optional for CE"}
              >
                <MenuItem value="">None</MenuItem>
                <MenuItem value="zoom">Zoom</MenuItem>
                <MenuItem value="google_meet">Google Meet</MenuItem>
              </TextField>
              <TextField label="Meeting type name (optional)" value={meetingName} onChange={(e) => setMeetingName(e.target.value)} fullWidth />
              <TextField
                type="number"
                label="Duration (minutes)"
                value={meetingMinutes}
                onChange={(e) => setMeetingMinutes(Number(e.target.value) || 30)}
                fullWidth
              />
              <Stack direction="row" spacing={1}>
                <Button onClick={() => setStep(1)}>Back</Button>
                <Button variant="contained" disabled={busy} onClick={() => void onSaveStep2()}>
                  Save channels
                </Button>
              </Stack>
            </>
          )}

          <Box sx={{ border: "1px solid", borderColor: "divider", p: 2, borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom>
              Readiness
            </Typography>
            {readiness ? (
              <Stack spacing={0.5}>
                <Typography variant="body2">
                  {readiness.ready ? "Ready to publish" : "Blocked"} · blockers: {readiness.blockers.join(", ") || "none"} ·
                  warnings: {readiness.warnings.join(", ") || "none"}
                </Typography>
                {readiness.checks.map((c) => (
                  <Typography key={c.key} variant="caption" display="block">
                    [{c.status}] {c.label}
                  </Typography>
                ))}
              </Stack>
            ) : (
              <Typography variant="body2">Complete the wizard to evaluate readiness.</Typography>
            )}
            <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
              <Button variant="contained" color="success" disabled={busy || !readiness?.ready || Boolean(profile?.published)} onClick={() => void onPublish()}>
                Publish
              </Button>
              <Button variant="outlined" disabled={busy || !profile?.published} onClick={() => void onUnpublish()}>
                Unpublish
              </Button>
            </Stack>
            {embedUrl ? (
              <Typography variant="body2" sx={{ mt: 1 }}>
                Public embed: {embedUrl}
              </Typography>
            ) : null}
          </Box>

          <Box sx={{ border: "1px solid", borderColor: "divider", p: 2, borderRadius: 1, bgcolor: "action.hover" }}>
            <Typography variant="subtitle2" gutterBottom>
              Live preview (visitor view)
            </Typography>
            <Typography variant="body1">{previewGreeting || greeting || "Greeting appears here after save."}</Typography>
            <Typography variant="caption" display="block" sx={{ mt: 1 }}>
              {businessName || "Business name"} · {personaName || "Persona"}
            </Typography>
          </Box>
        </Stack>
      ) : (
        <Alert severity="info">
          {TABS[tab]} will receive external customer data after the setup wizard publishes a concierge. viCal bookings, CRM, and
          outreach remain in their own areas.
        </Alert>
      )}
    </Box>
  );
}
