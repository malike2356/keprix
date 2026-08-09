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
  addCaseNote,
  beginZoomConnect,
  createKnowledge,
  fetchAnalytics,
  fetchAudienceTools,
  fetchBookingMesh,
  fetchChannels,
  fetchConciergeBookings,
  fetchConciergeProfile,
  fetchCustomerCase,
  fetchCustomerCases,
  fetchKnowledge,
  fetchLeadsTable,
  fetchPreview,
  fetchReadiness,
  fetchSessionMessages,
  fetchZoomConnection,
  patchChannels,
  publishConcierge,
  releaseSession,
  revokeZoomConnection,
  saveStep1,
  saveStep2,
  setBookingOutcome,
  setKnowledgePublishState,
  takeoverSession,
  testZoomConnection,
  unpublishConcierge,
  type ChannelRow,
  type ConciergeBooking,
  type ConciergeProfile,
  type CustomerCase,
  type KnowledgeSource,
  type Readiness,
  type ZoomConnection,
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
  const [sources, setSources] = React.useState<KnowledgeSource[]>([]);
  const [kbTitle, setKbTitle] = React.useState("");
  const [kbContent, setKbContent] = React.useState("");
  const [cases, setCases] = React.useState<CustomerCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = React.useState<string | null>(null);
  const [caseNotes, setCaseNotes] = React.useState<Array<{ id: string; body: string }>>([]);
  const [noteDraft, setNoteDraft] = React.useState("");
  const [casesNote, setCasesNote] = React.useState<string | null>(null);
  const [zoom, setZoom] = React.useState<ZoomConnection | null>(null);
  const [zoomDetail, setZoomDetail] = React.useState<string | null>(null);
  const [bookings, setBookings] = React.useState<ConciergeBooking[]>([]);
  const [leadRows, setLeadRows] = React.useState<Array<Record<string, unknown>>>([]);
  const [meshDetail, setMeshDetail] = React.useState<string | null>(null);
  const [channels, setChannels] = React.useState<ChannelRow[]>([]);
  const [channelNote, setChannelNote] = React.useState<string | null>(null);
  const [analytics, setAnalytics] = React.useState<{
    metrics: Record<string, unknown>;
    derived: Record<string, number>;
  } | null>(null);
  const [sessionMessages, setSessionMessages] = React.useState<
    Array<{ role: string; body: string }>
  >([]);
  const [audienceTools, setAudienceTools] = React.useState<string[]>([]);

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
                helperText="IDs of published business sources (manage under Knowledge tab)"
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
      ) : tab === 3 ? (
        <Stack spacing={2} sx={{ maxWidth: 720 }}>
          <Alert severity="info">
            Tenant published business knowledge only. This is not the Keprix product self-support corpus.
          </Alert>
          <TextField label="Title" value={kbTitle} onChange={(e) => setKbTitle(e.target.value)} fullWidth />
          <TextField
            label="Content"
            value={kbContent}
            onChange={(e) => setKbContent(e.target.value)}
            fullWidth
            multiline
            minRows={4}
          />
          <Button
            variant="contained"
            disabled={busy || !kbTitle.trim() || !kbContent.trim()}
            onClick={() => {
              void (async () => {
                setBusy(true);
                setError(null);
                try {
                  await createKnowledge({
                    personaId,
                    title: kbTitle.trim(),
                    content: kbContent.trim(),
                    type: "faq",
                    attachToProfile: true,
                  });
                  setKbTitle("");
                  setKbContent("");
                  const kb = await fetchKnowledge(personaId);
                  setSources(kb.sources);
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Knowledge save failed");
                } finally {
                  setBusy(false);
                }
              })();
            }}
          >
            Save draft source
          </Button>
          <Button
            variant="outlined"
            disabled={busy}
            onClick={() => {
              void (async () => {
                try {
                  const kb = await fetchKnowledge(personaId);
                  setSources(kb.sources);
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Knowledge load failed");
                }
              })();
            }}
          >
            Refresh sources
          </Button>
          <Stack spacing={1}>
            {sources.map((s) => (
              <Box key={s.id} sx={{ border: "1px solid", borderColor: "divider", p: 1.5, borderRadius: 1 }}>
                <Typography variant="subtitle2">
                  {s.title} · {s.publishState} · rev {s.revision}
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                  {s.content.slice(0, 240)}
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                  {s.publishState !== "published" ? (
                    <Button
                      size="small"
                      onClick={() => {
                        void (async () => {
                          await setKnowledgePublishState(s.id, "published");
                          setSources((await fetchKnowledge(personaId)).sources);
                        })();
                      }}
                    >
                      Publish
                    </Button>
                  ) : (
                    <Button
                      size="small"
                      onClick={() => {
                        void (async () => {
                          await setKnowledgePublishState(s.id, "archived");
                          setSources((await fetchKnowledge(personaId)).sources);
                        })();
                      }}
                    >
                      Archive
                    </Button>
                  )}
                </Stack>
              </Box>
            ))}
            {!sources.length ? <Typography variant="body2">No knowledge sources yet.</Typography> : null}
          </Stack>
        </Stack>
      ) : tab === 1 ? (
        <Stack spacing={2} sx={{ maxWidth: 800 }}>
          <Alert severity="warning">
            Customer support cases for your visitors ({casesNote || "tenant_customer_support"}). Keprix product-support tickets
            stay under /api/support and must not be mixed here.
          </Alert>
          <Button
            variant="outlined"
            onClick={() => {
              void (async () => {
                try {
                  const data = await fetchCustomerCases(personaId);
                  setCases(data.cases);
                  setCasesNote(`${data.scope} (not ${data.productSupportScope})`);
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Cases load failed");
                }
              })();
            }}
          >
            Refresh cases
          </Button>
          <Stack spacing={1}>
            {cases.map((c) => (
              <Box key={c.id} sx={{ border: "1px solid", borderColor: "divider", p: 1.5, borderRadius: 1 }}>
                <Typography variant="subtitle2">
                  {c.subject} · {c.status} · {c.priority}
                </Typography>
                <Typography variant="caption" display="block">
                  scope={c.scope} · session={c.audienceSessionId || "n/a"}
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                  <Button
                    size="small"
                    onClick={() => {
                      void (async () => {
                        setSelectedCaseId(c.id);
                        const detail = await fetchCustomerCase(c.id);
                        setCaseNotes(detail.internalNotes.map((n) => ({ id: n.id, body: n.body })));
                      })();
                    }}
                  >
                    Open
                  </Button>
                  {c.audienceSessionId ? (
                    <>
                      <Button
                        size="small"
                        onClick={() => {
                          void (async () => {
                            const msgs = await fetchSessionMessages(c.audienceSessionId as string);
                            setSessionMessages(msgs.messages.map((m) => ({ role: m.role, body: m.body })));
                          })();
                        }}
                      >
                        Thread
                      </Button>
                      <Button
                        size="small"
                        onClick={() => {
                          void takeoverSession(c.audienceSessionId as string);
                        }}
                      >
                        Takeover
                      </Button>
                      <Button
                        size="small"
                        onClick={() => {
                          void releaseSession(c.audienceSessionId as string);
                        }}
                      >
                        Release to AI
                      </Button>
                    </>
                  ) : null}
                </Stack>
              </Box>
            ))}
            {!cases.length ? <Typography variant="body2">No customer cases yet.</Typography> : null}
          </Stack>
          {sessionMessages.length ? (
            <Box sx={{ border: "1px solid", borderColor: "divider", p: 2, borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                Originating thread (channel continuous)
              </Typography>
              {sessionMessages.map((m, idx) => (
                <Typography key={`${m.role}-${idx}`} variant="body2" sx={{ mb: 0.75 }}>
                  <strong>{m.role}:</strong> {m.body}
                </Typography>
              ))}
            </Box>
          ) : null}
          {selectedCaseId ? (
            <Box sx={{ border: "1px solid", borderColor: "divider", p: 2, borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                Internal notes (owner only) · case {selectedCaseId}
              </Typography>
              {caseNotes.map((n) => (
                <Typography key={n.id} variant="body2" sx={{ mb: 1 }}>
                  {n.body}
                </Typography>
              ))}
              <TextField
                label="Add internal note"
                value={noteDraft}
                onChange={(e) => setNoteDraft(e.target.value)}
                fullWidth
                multiline
                minRows={2}
              />
              <Button
                sx={{ mt: 1 }}
                variant="contained"
                disabled={!noteDraft.trim()}
                onClick={() => {
                  void (async () => {
                    await addCaseNote(selectedCaseId, noteDraft.trim());
                    setNoteDraft("");
                    const detail = await fetchCustomerCase(selectedCaseId);
                    setCaseNotes(detail.internalNotes.map((n) => ({ id: n.id, body: n.body })));
                  })();
                }}
              >
                Save note
              </Button>
            </Box>
          ) : null}
        </Stack>
      ) : tab === 2 ? (
        <Stack spacing={2} sx={{ maxWidth: 960 }}>
          <Alert severity="info">
            One booking record across viCal, Calendar, CRM, and Outreach. Soft Wall rows link via vical:id.
          </Alert>
          <Stack direction="row" spacing={1}>
            <Button
              variant="outlined"
              onClick={() => {
                void (async () => {
                  try {
                    const data = await fetchConciergeBookings();
                    setBookings(data.bookings);
                    setLeadRows(data.spreadsheetRows);
                    setMeshDetail(null);
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Bookings load failed");
                  }
                })();
              }}
            >
              Refresh bookings
            </Button>
            <Button
              variant="outlined"
              onClick={() => {
                void (async () => {
                  const data = await fetchLeadsTable();
                  setLeadRows(data.rows);
                })();
              }}
            >
              Lead table rows
            </Button>
          </Stack>
          <Stack spacing={1}>
            {bookings.map((b) => (
              <Box key={b.id} sx={{ border: "1px solid", borderColor: "divider", p: 1.5, borderRadius: 1 }}>
                <Typography variant="subtitle2">
                  {b.guestName} · {b.guestEmail} · {b.status}
                </Typography>
                <Typography variant="caption" display="block">
                  {b.startsAt || "n/a"} · meeting={b.meetingUrl || "ics/fallback"}
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                  <Button
                    size="small"
                    onClick={() => {
                      void (async () => {
                        const res = await fetchBookingMesh(b.id);
                        setMeshDetail(JSON.stringify(res.mesh?.mesh || res.mesh, null, 2));
                      })();
                    }}
                  >
                    Mesh chain
                  </Button>
                  <Button
                    size="small"
                    onClick={() => {
                      void setBookingOutcome(b.id, "completed", true);
                    }}
                  >
                    Mark converted
                  </Button>
                  <Button size="small" href="/vical" component="a">
                    Open viCal
                  </Button>
                  <Button size="small" href="/crm" component="a">
                    Open CRM
                  </Button>
                </Stack>
              </Box>
            ))}
            {!bookings.length ? <Typography variant="body2">No bookings yet.</Typography> : null}
          </Stack>
          {meshDetail ? (
            <Box component="pre" sx={{ p: 1.5, bgcolor: "action.hover", overflow: "auto", fontSize: 12 }}>
              {meshDetail}
            </Box>
          ) : null}
          {leadRows.length ? (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Spreadsheet lead columns (privacy-safe ids)
              </Typography>
              {leadRows.slice(0, 20).map((row) => (
                <Typography key={String(row.bookingId)} variant="caption" display="block">
                  {String(row.guestEmail)} · {String(row.status)} · booking={String(row.bookingId)} · crm=
                  {String(row.crmLeadId || row.crmContactId || "-")} · outreach=
                  {String(row.outreachLeadId || "-")}
                </Typography>
              ))}
            </Box>
          ) : null}
        </Stack>
      ) : tab === 4 ? (
        <Stack spacing={2} sx={{ maxWidth: 800 }}>
          <Alert severity="info">
            Channel replies stay in the originating thread. Audience tools only; no owner privileges on visitor
            surfaces (web, gateway, phone, desktop, TUI).
          </Alert>
          <Button
            variant="outlined"
            onClick={() => {
              void (async () => {
                try {
                  const data = await fetchChannels(personaId);
                  setChannels(data.channels);
                  setChannelNote(data.note);
                  const tools = await fetchAudienceTools("web");
                  setAudienceTools(tools.allowedTools);
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Channels load failed");
                }
              })();
            }}
          >
            Refresh channels
          </Button>
          {channelNote ? <Typography variant="body2">{channelNote}</Typography> : null}
          <Stack spacing={1}>
            {channels.map((ch) => (
              <Box key={ch.key} sx={{ border: "1px solid", borderColor: "divider", p: 1.5, borderRadius: 1 }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={ch.enabled}
                      onChange={(e) => {
                        void (async () => {
                          const res = await patchChannels(personaId, {
                            [ch.key]: { enabled: e.target.checked },
                          });
                          setChannels(res.channels);
                        })();
                      }}
                    />
                  }
                  label={`${ch.key} · connected=${String(ch.connected)} · consent=${String(ch.consentRequired)}`}
                />
                {ch.setup ? (
                  <Typography variant="caption" display="block">
                    {ch.setup}
                  </Typography>
                ) : null}
              </Box>
            ))}
          </Stack>
          {audienceTools.length ? (
            <Typography variant="caption" display="block">
              Audience tools ({audienceTools.length}): {audienceTools.slice(0, 8).join(", ")}…
            </Typography>
          ) : null}
        </Stack>
      ) : tab === 6 ? (
        <Stack spacing={2} sx={{ maxWidth: 720 }}>
          <Alert severity="info">Metrics are event-derived and privacy-safe (no message bodies or host start URLs).</Alert>
          <Button
            variant="outlined"
            onClick={() => {
              void (async () => {
                try {
                  const data = await fetchAnalytics(personaId);
                  setAnalytics({ metrics: data.metrics, derived: data.derived });
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Analytics load failed");
                }
              })();
            }}
          >
            Refresh analytics
          </Button>
          {analytics ? (
            <Box sx={{ border: "1px solid", borderColor: "divider", p: 2, borderRadius: 1 }}>
              <Typography variant="body2">Confirmed: {String(analytics.metrics.confirmedBookings)}</Typography>
              <Typography variant="body2">Bookings total: {String(analytics.metrics.bookingsTotal)}</Typography>
              <Typography variant="body2">Handoffs: {String(analytics.metrics.handoffs)}</Typography>
              <Typography variant="body2">Takeovers: {String(analytics.metrics.takeovers)}</Typography>
              <Typography variant="body2">
                Confirm rate: {Number(analytics.derived.confirmRate || 0).toFixed(2)} · Cancel rate:{" "}
                {Number(analytics.derived.cancelRate || 0).toFixed(2)}
              </Typography>
            </Box>
          ) : (
            <Typography variant="body2">Load analytics to report on concierge activity.</Typography>
          )}
        </Stack>
      ) : tab === 5 ? (
        <Stack spacing={2} sx={{ maxWidth: 720 }}>
          <Alert severity="info">
            Zoom uses your own OAuth app credentials (ZOOM_CLIENT_ID / SECRET). No VERLOX-hosted credential service is required.
            Static room URLs and ICS remain labelled unmanaged fallbacks.
          </Alert>
          <Button
            variant="outlined"
            onClick={() => {
              void (async () => {
                try {
                  setZoom(await fetchZoomConnection());
                  setZoomDetail(null);
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Zoom status failed");
                }
              })();
            }}
          >
            Refresh Zoom status
          </Button>
          {zoom ? (
            <Box sx={{ border: "1px solid", borderColor: "divider", p: 2, borderRadius: 1 }}>
              <Typography variant="subtitle2">Status: {zoom.status}</Typography>
              <Typography variant="body2">OAuth configured: {String(zoom.oauthConfigured)}</Typography>
              <Typography variant="body2">Connected: {String(zoom.connected)}</Typography>
              <Typography variant="body2">Account: {zoom.accountEmail || "n/a"}</Typography>
              <Typography variant="body2">Scopes: {(zoom.scopes || []).join(" ") || "n/a"}</Typography>
              <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                Fallback: static URL={String(zoom.fallback?.staticRoomUrl)} · ICS={String(zoom.fallback?.icsFallback)} ·
                claims managed Zoom={String(zoom.fallback?.claimsManagedZoom)}
              </Typography>
            </Box>
          ) : null}
          {zoomDetail ? <Alert severity="success">{zoomDetail}</Alert> : null}
          <Stack direction="row" spacing={1}>
            <Button
              variant="contained"
              onClick={() => {
                void (async () => {
                  const redirectUri = `${window.location.origin}/concierge`;
                  const res = await beginZoomConnect(redirectUri);
                  if (res.authorizeUrl) {
                    window.open(res.authorizeUrl, "_blank", "noopener,noreferrer");
                  } else {
                    setError(res.error_code || "Zoom connect unavailable");
                  }
                })();
              }}
            >
              Connect / reconnect
            </Button>
            <Button
              variant="outlined"
              onClick={() => {
                void (async () => {
                  const res = await testZoomConnection();
                  setZoomDetail(res.detail || (res.ok ? "Zoom test ok" : "Zoom test failed"));
                  setZoom(await fetchZoomConnection());
                })();
              }}
            >
              Test
            </Button>
            <Button
              color="warning"
              variant="outlined"
              onClick={() => {
                void (async () => {
                  await revokeZoomConnection();
                  setZoom(await fetchZoomConnection());
                  setZoomDetail("Zoom connection revoked");
                })();
              }}
            >
              Revoke
            </Button>
          </Stack>
        </Stack>
      ) : (
        <Alert severity="info">{TABS[tab]} is loading operator controls.</Alert>
      )}
    </Box>
  );
}
