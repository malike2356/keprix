"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import MeshRelatedLinks, { buildVicalRelatedLinks } from "@/components/vical/MeshRelatedLinks";
import {
  approveBooking,
  cancelBooking,
  createAvailabilityRule,
  createBlackout,
  createEventType,
  createIntakePool,
  fetchAvailabilityRules,
  fetchBlackouts,
  fetchBookings,
  fetchEventTypes,
  fetchHostProfile,
  fetchIntakePools,
  fetchVicalStatus,
  patchEventType,
  rejectBooking,
  seedVical,
  updateHostProfile,
  type VicalBooking,
  type VicalEventType,
} from "@/lib/vical-api";

function statusColor(status: string): "success" | "warning" | "default" | "error" {
  if (status === "confirmed") return "success";
  if (status === "pending_review" || status === "pending_payment") return "warning";
  if (status === "cancelled" || status === "rejected") return "error";
  return "default";
}

export default function VicalHubPage() {
  const [tab, setTab] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [publicPath, setPublicPath] = React.useState("/book/");
  const [bookings, setBookings] = React.useState<VicalBooking[]>([]);
  const [types, setTypes] = React.useState<VicalEventType[]>([]);
  const [rules, setRules] = React.useState<Array<Record<string, unknown>>>([]);
  const [blackouts, setBlackouts] = React.useState<Array<Record<string, unknown>>>([]);
  const [pools, setPools] = React.useState<Array<Record<string, unknown>>>([]);
  const [selected, setSelected] = React.useState<VicalBooking | null>(null);
  const [slugInput, setSlugInput] = React.useState("");
  const [displayName, setDisplayName] = React.useState("");
  const [newTypeName, setNewTypeName] = React.useState("");
  const [newTypeSlug, setNewTypeSlug] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await seedVical().catch(() => undefined);
      const [status, profile, bookingRows, typeRows, ruleRows, blackoutRows, poolRows] = await Promise.all([
        fetchVicalStatus(),
        fetchHostProfile(),
        fetchBookings(),
        fetchEventTypes(),
        fetchAvailabilityRules(),
        fetchBlackouts(),
        fetchIntakePools(),
      ]);
      setPublicPath(status.public_book_path || profile.public_book_path || "/book/");
      setSlugInput(profile.profile.public_slug || "");
      setDisplayName(profile.profile.display_name || "");
      setBookings(bookingRows);
      setTypes(typeRows);
      setRules(ruleRows);
      setBlackouts(blackoutRows);
      setPools(poolRows);
      if (!selected && bookingRows.length) setSelected(bookingRows[0]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load viCal");
    } finally {
      setLoading(false);
    }
  }, [selected]);

  React.useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function saveProfile() {
    setBusy(true);
    setError(null);
    try {
      const result = await updateHostProfile({
        public_slug: slugInput.trim() || undefined,
        display_name: displayName.trim() || undefined,
      });
      setPublicPath(result.public_book_path);
      setSlugInput(result.profile.public_slug || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    } finally {
      setBusy(false);
    }
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}${publicPath}`);
    } catch {
      setError("Could not copy link");
    }
  }

  async function addConsultationSeedRules() {
    setBusy(true);
    try {
      for (let day = 0; day < 5; day += 1) {
        await createAvailabilityRule({ day_of_week: day, start_time: "09:00", end_time: "17:00" });
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add availability");
    } finally {
      setBusy(false);
    }
  }

  async function addType() {
    if (!newTypeName.trim() || !newTypeSlug.trim()) return;
    setBusy(true);
    try {
      await createEventType({ slug: newTypeSlug.trim(), name: newTypeName.trim(), duration_minutes: 30 });
      setNewTypeName("");
      setNewTypeSlug("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create event type");
    } finally {
      setBusy(false);
    }
  }

  async function addSampleIntake(eventTypeId: string) {
    setBusy(true);
    try {
      const pool = await createIntakePool({
        name: "Qualify",
        questions: [
          {
            id: "ready",
            label: "Are you ready to book a live session?",
            type: "single_select",
            required: true,
            options: ["yes", "no"],
            disqualify_answers: ["no"],
            disqualify_message: "Please come back when you are ready.",
          },
        ],
      });
      await patchEventType(eventTypeId, { intake_pool_id: String(pool.id) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not attach intake");
    } finally {
      setBusy(false);
    }
  }

  async function addBlackoutToday() {
    const today = new Date().toISOString().slice(0, 10);
    setBusy(true);
    try {
      await createBlackout({ starts_on: today, ends_on: today, reason: "Unavailable" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add blackout");
    } finally {
      setBusy(false);
    }
  }

  async function act(kind: "approve" | "reject" | "cancel", id: string) {
    setBusy(true);
    try {
      const fn = kind === "approve" ? approveBooking : kind === "reject" ? rejectBooking : cancelBooking;
      const updated = await fn(id);
      setBookings((prev) => prev.map((b) => (b.id === updated.id ? updated : b)));
      setSelected(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const upcoming = bookings.filter((b) => ["confirmed", "pending_review", "pending_payment"].includes(b.status));

  return (
    <Box sx={{ p: { xs: 2, md: 3 }, maxWidth: 1200, mx: "auto" }}>
      <PageHeader
        title="viCal"
        description="Event types, availability, and booking inbox. Public guests book via your share link."
      />
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {loading ? (
        <CircularProgress size={28} />
      ) : (
        <>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 2 }} alignItems={{ sm: "center" }}>
            <TextField
              size="small"
              label="Public slug"
              value={slugInput}
              onChange={(e) => setSlugInput(e.target.value)}
              sx={{ minWidth: 160 }}
            />
            <TextField
              size="small"
              label="Display name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              sx={{ minWidth: 180 }}
            />
            <Button variant="contained" onClick={() => void saveProfile()} disabled={busy}>
              Save
            </Button>
            <Button variant="outlined" onClick={() => void copyLink()}>
              Copy public link
            </Button>
            <Typography variant="body2" color="text.secondary">
              {publicPath}
            </Typography>
          </Stack>

          <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }} variant="scrollable">
            <Tab label="Overview" />
            <Tab label="Bookings" />
            <Tab label="Event types" />
            <Tab label="Availability" />
            <Tab label="Intake" />
          </Tabs>

          {tab === 0 ? (
            <Box>
              <Typography variant="subtitle1" sx={{ mb: 1 }}>
                Upcoming ({upcoming.length})
              </Typography>
              {upcoming.length === 0 ? (
                <EmptyState
                  title="No bookings yet"
                  description="Share your public link so guests can book a Consultation."
                  actionLabel="Copy public link"
                  onAction={() => void copyLink()}
                />
              ) : (
                <Stack spacing={1}>
                  {upcoming.slice(0, 8).map((b) => (
                    <Stack
                      key={b.id}
                      direction="row"
                      spacing={1}
                      alignItems="center"
                      sx={{ py: 1, borderBottom: "1px solid", borderColor: "divider" }}
                    >
                      <Chip size="small" label={b.status} color={statusColor(b.status)} />
                      <Typography variant="body2" sx={{ flex: 1 }}>
                        {b.guest_name} · {new Date(b.starts_at).toLocaleString()}
                      </Typography>
                      <Button size="small" onClick={() => { setSelected(b); setTab(1); }}>
                        Open
                      </Button>
                    </Stack>
                  ))}
                </Stack>
              )}
            </Box>
          ) : null}

          {tab === 1 ? (
            <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ minHeight: 320 }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                {bookings.length === 0 ? (
                  <EmptyState title="Inbox empty" description="New requests appear here." />
                ) : (
                  bookings.map((b) => (
                    <Box
                      key={b.id}
                      onClick={() => setSelected(b)}
                      sx={{
                        p: 1.25,
                        cursor: "pointer",
                        bgcolor: selected?.id === b.id ? "action.selected" : "transparent",
                        borderBottom: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip size="small" label={b.status} color={statusColor(b.status)} />
                        <Typography variant="body2">{b.guest_name}</Typography>
                      </Stack>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(b.starts_at).toLocaleString()} · {b.guest_email}
                      </Typography>
                    </Box>
                  ))
                )}
              </Box>
              <Divider orientation="vertical" flexItem sx={{ display: { xs: "none", md: "block" } }} />
              <Box sx={{ flex: 1.2, minWidth: 0 }}>
                {!selected ? (
                  <Typography color="text.secondary">Select a booking</Typography>
                ) : (
                  <Stack spacing={1.5}>
                    <Typography variant="h6">{selected.guest_name}</Typography>
                    <Typography variant="body2">{selected.guest_email}</Typography>
                    <Typography variant="body2">
                      {new Date(selected.starts_at).toLocaleString()} - {new Date(selected.ends_at).toLocaleString()}
                    </Typography>
                    <Chip size="small" label={selected.status} color={statusColor(selected.status)} sx={{ alignSelf: "flex-start" }} />
                    {selected.intake_answers && Object.keys(selected.intake_answers).length ? (
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Intake
                        </Typography>
                        <Typography variant="body2" component="pre" sx={{ m: 0, whiteSpace: "pre-wrap" }}>
                          {JSON.stringify(selected.intake_answers, null, 2)}
                        </Typography>
                      </Box>
                    ) : null}
                    <Stack direction="row" spacing={1} flexWrap="wrap">
                      {selected.status === "pending_review" ? (
                        <>
                          <Button variant="contained" disabled={busy} onClick={() => void act("approve", selected.id)}>
                            Approve
                          </Button>
                          <Button color="warning" disabled={busy} onClick={() => void act("reject", selected.id)}>
                            Reject
                          </Button>
                        </>
                      ) : null}
                      {["confirmed", "pending_payment", "pending_review"].includes(selected.status) ? (
                        <Button color="error" disabled={busy} onClick={() => void act("cancel", selected.id)}>
                          Cancel
                        </Button>
                      ) : null}
                    </Stack>
                    <Typography variant="subtitle2" sx={{ mt: 1 }}>
                      Related
                    </Typography>
                    <MeshRelatedLinks
                      links={buildVicalRelatedLinks({
                        bookingId: selected.id,
                        workspaceEventId: selected.workspace_event_id,
                        contactId: selected.contact_id,
                        publicBookPath: publicPath,
                      })}
                    />
                  </Stack>
                )}
              </Box>
            </Stack>
          ) : null}

          {tab === 2 ? (
            <Box>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 2 }}>
                <TextField size="small" label="Name" value={newTypeName} onChange={(e) => setNewTypeName(e.target.value)} />
                <TextField size="small" label="Slug" value={newTypeSlug} onChange={(e) => setNewTypeSlug(e.target.value)} />
                <Button variant="contained" disabled={busy} onClick={() => void addType()}>
                  Add type
                </Button>
              </Stack>
              {types.map((et) => (
                <Stack
                  key={et.id}
                  direction={{ xs: "column", sm: "row" }}
                  spacing={1}
                  alignItems={{ sm: "center" }}
                  sx={{ py: 1, borderBottom: "1px solid", borderColor: "divider" }}
                >
                  <Typography sx={{ flex: 1 }}>
                    {et.name} ({et.slug}) · {et.duration_minutes}m
                  </Typography>
                  {et.requires_approval ? <Chip size="small" label="approval" /> : null}
                  {et.requires_deposit ? <Chip size="small" label="deposit" /> : null}
                  {et.intake_pool_id ? <Chip size="small" label="intake" color="info" /> : null}
                  {!et.intake_pool_id ? (
                    <Button size="small" disabled={busy} onClick={() => void addSampleIntake(et.id)}>
                      Attach sample intake
                    </Button>
                  ) : null}
                </Stack>
              ))}
            </Box>
          ) : null}

          {tab === 3 ? (
            <Box>
              <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                <Button variant="outlined" disabled={busy} onClick={() => void addConsultationSeedRules()}>
                  Add Mon-Fri 09-17
                </Button>
                <Button variant="outlined" disabled={busy} onClick={() => void addBlackoutToday()}>
                  Blackout today
                </Button>
              </Stack>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Rules ({rules.length})
              </Typography>
              {rules.map((r) => (
                <Typography key={String(r.id)} variant="body2" sx={{ py: 0.5 }}>
                  Day {String(r.day_of_week)} · {String(r.start_time)}-{String(r.end_time)} ({String(r.timezone)})
                </Typography>
              ))}
              <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                Blackouts ({blackouts.length})
              </Typography>
              {blackouts.map((b) => (
                <Typography key={String(b.id)} variant="body2" sx={{ py: 0.5 }}>
                  {String(b.starts_on)} - {String(b.ends_on)} {b.reason ? `· ${String(b.reason)}` : ""}
                </Typography>
              ))}
            </Box>
          ) : null}

          {tab === 4 ? (
            <Box>
              {pools.length === 0 ? (
                <EmptyState
                  title="No intake pools"
                  description="Attach a sample intake from an event type, or create pools via API."
                />
              ) : (
                pools.map((p) => (
                  <Box key={String(p.id)} sx={{ py: 1, borderBottom: "1px solid", borderColor: "divider" }}>
                    <Typography variant="body1">{String(p.name)}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {Array.isArray(p.questions) ? p.questions.length : 0} questions · id {String(p.id)}
                    </Typography>
                  </Box>
                ))
              )}
            </Box>
          ) : null}
        </>
      )}
    </Box>
  );
}
