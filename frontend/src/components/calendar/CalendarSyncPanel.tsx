"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import SyncIcon from "@mui/icons-material/Sync";
import LinkIcon from "@mui/icons-material/Link";
import * as React from "react";
import { keprixConfirm } from "@/components/ui/confirm/KeprixConfirm";
import {
  createCalendarSource,
  deleteCalendarSource,
  fetchCalendarAutoSyncStatus,
  fetchCalendarGoogleAuthUrl,
  fetchCalendarGoogleOAuthConfig,
  fetchCalendarProviders,
  fetchCalendarSources,
  saveCalendarGoogleOAuthConfig,
  syncCalendarSource,
  syncCalendarSources,
  updateCalendarSource,
  type CalendarAutoSyncStatus,
  type CalendarGoogleOAuthConfig,
  type CalendarProviderPreset,
  type CalendarSource,
} from "@/lib/workspace-api";

type Props = {
  onSynced?: () => void;
};

const INTERVAL_OPTIONS = [5, 15, 30, 60, 120, 360, 720, 1440];

export default function CalendarSyncPanel({ onSynced }: Props) {
  const [open, setOpen] = React.useState(false);
  const [connectOpen, setConnectOpen] = React.useState(false);
  const [sources, setSources] = React.useState<CalendarSource[]>([]);
  const [providers, setProviders] = React.useState<CalendarProviderPreset[]>([]);
  const [autoStatus, setAutoStatus] = React.useState<CalendarAutoSyncStatus | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [syncing, setSyncing] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [status, setStatus] = React.useState<string | null>(null);

  const [presetId, setPresetId] = React.useState("google");
  const [name, setName] = React.useState("Google Calendar");
  const [url, setUrl] = React.useState("");
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [syncDirection, setSyncDirection] = React.useState("bidirectional");
  const [calendarName, setCalendarName] = React.useState("");
  const [pushLocal, setPushLocal] = React.useState(true);
  const [autoSync, setAutoSync] = React.useState(true);
  const [intervalMinutes, setIntervalMinutes] = React.useState(15);
  const [saving, setSaving] = React.useState(false);
  const [googleConfig, setGoogleConfig] = React.useState<CalendarGoogleOAuthConfig | null>(null);
  const [googleModalOpen, setGoogleModalOpen] = React.useState(false);
  const [googleClientId, setGoogleClientId] = React.useState("");
  const [googleClientSecret, setGoogleClientSecret] = React.useState("");
  const [googleSaving, setGoogleSaving] = React.useState(false);
  const [icsRepairId, setIcsRepairId] = React.useState<string | null>(null);
  const [icsRepairUrl, setIcsRepairUrl] = React.useState("");

  const preset = providers.find((item) => item.id === presetId) || providers[0];

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextSources, nextProviders, nextAuto, nextGoogle] = await Promise.all([
        fetchCalendarSources(),
        fetchCalendarProviders(),
        fetchCalendarAutoSyncStatus().catch(() => null),
        fetchCalendarGoogleOAuthConfig().catch(() => null),
      ]);
      setSources(nextSources);
      setProviders(nextProviders);
      setAutoStatus(nextAuto);
      if (nextGoogle) setGoogleConfig(nextGoogle);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load calendar sources");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const google = params.get("google");
    const oauthError = params.get("error");
    if (!google && !oauthError) return;
    setOpen(true);
    if (oauthError || google === "error") {
      setError(oauthError || "Google Calendar OAuth failed");
    } else if (google === "connected") {
      setStatus("Google Calendar connected. Events will appear after the first sync.");
    }
    params.delete("google");
    params.delete("error");
    const next = `${window.location.pathname}${params.toString() ? `?${params}` : ""}`;
    window.history.replaceState({}, "", next);
  }, []);

  React.useEffect(() => {
    if (open) {
      void load();
    }
  }, [open, load]);

  function applyPreset(nextId: string) {
    setPresetId(nextId);
    const next = providers.find((item) => item.id === nextId);
    if (!next) return;
    setName(next.label);
    const twoWay = next.sync_modes.includes("bidirectional");
    setSyncDirection(twoWay ? "bidirectional" : next.sync_modes[0] || "pull");
    setPushLocal(twoWay);
    setAutoSync(true);
    setIntervalMinutes(15);
  }

  async function handleSyncAll() {
    setSyncing(true);
    setError(null);
    setStatus(null);
    try {
      const result = await syncCalendarSources();
      setStatus(result.message || (result.ok ? "Sync complete" : "Sync finished with errors"));
      await load();
      onSynced?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  async function handleSyncOne(sourceId: string) {
    setSyncing(true);
    setError(null);
    try {
      const result = await syncCalendarSource(sourceId);
      setStatus(result.message || "Source synced");
      await load();
      onSynced?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Source sync failed");
    } finally {
      setSyncing(false);
    }
  }

  async function handleConnect() {
    if (!preset || !name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const created = await createCalendarSource({
        name: name.trim(),
        provider: preset.provider,
        url: url.trim() || undefined,
        username: username.trim() || undefined,
        password: password || undefined,
        sync_direction: syncDirection,
        calendar_name: calendarName.trim() || undefined,
        push_local_events: pushLocal && preset.provider !== "ics",
        auto_sync: autoSync,
        sync_interval_minutes: intervalMinutes,
      });
      setConnectOpen(false);
      setPassword("");
      setUrl("");
      setUsername("");
      setCalendarName("");
      await load();
      onSynced?.();
      if (created.last_sync_ok === false) {
        setStatus(null);
        setError(
          created.last_sync_message ||
            "Calendar connected, but the first sync failed. Check the token and click Sync.",
        );
      } else {
        setStatus(
          created.last_sync_message ||
            (autoSync
              ? `Calendar connected. Auto 2-way sync every ${intervalMinutes} min (ICS stays pull-only).`
              : "Calendar connected. Auto-sync is off; use Sync manually."),
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect calendar");
    } finally {
      setSaving(false);
    }
  }

  async function connectGoogleOAuth() {
    setError(null);
    try {
      const config = googleConfig || (await fetchCalendarGoogleOAuthConfig());
      setGoogleConfig(config);
      if (!config.configured) {
        setGoogleModalOpen(true);
        return;
      }
      window.location.href = await fetchCalendarGoogleAuthUrl();
    } catch (err) {
      setGoogleModalOpen(true);
      setError(err instanceof Error ? err.message : "Google Calendar OAuth is not configured");
    }
  }

  async function saveGoogleCredentialsAndConnect() {
    if (!googleClientId.trim() || !googleClientSecret.trim()) {
      setError("Client ID and Client Secret are required");
      return;
    }
    setGoogleSaving(true);
    setError(null);
    try {
      const saved = await saveCalendarGoogleOAuthConfig({
        client_id: googleClientId.trim(),
        client_secret: googleClientSecret.trim(),
      });
      setGoogleConfig(saved);
      setGoogleClientSecret("");
      setGoogleModalOpen(false);
      setStatus("Google OAuth app saved. Continuing to Google consent…");
      window.location.href = await fetchCalendarGoogleAuthUrl();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save Google credentials");
    } finally {
      setGoogleSaving(false);
    }
  }

  async function repairWithIcs(sourceId: string) {
    const nextUrl = icsRepairUrl.trim();
    if (!nextUrl.toLowerCase().includes(".ics")) {
      setError("Paste the secret iCal URL from Google Calendar settings (it ends in .ics).");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await updateCalendarSource(sourceId, { url: nextUrl, provider: "ics" });
      setIcsRepairId(null);
      setIcsRepairUrl("");
      const result = await syncCalendarSource(sourceId);
      setStatus(result.message || "ICS feed connected");
      await load();
      onSynced?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to switch to ICS feed");
    } finally {
      setSaving(false);
    }
  }

  async function handleRemove(source: CalendarSource) {
    if (!(await keprixConfirm({
      title: `Disconnect "${source.name}"?`,
      description: "Calendar syncing will stop. You can choose whether to delete imported events next.",
      confirmLabel: "Disconnect calendar source",
      destructive: true,
    }))) return;
    const dropEvents = await keprixConfirm({
      title: "Delete imported events?",
      description: "Delete events that were imported from this source. Choose Keep imported events to leave them in Keprix.",
      confirmLabel: "Delete imported events",
      cancelLabel: "Keep imported events",
      destructive: true,
    });
    try {
      await deleteCalendarSource(source.id, dropEvents);
      await load();
      onSynced?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove source");
    }
  }

  async function patchSource(sourceId: string, body: Parameters<typeof updateCalendarSource>[1]) {
    try {
      await updateCalendarSource(sourceId, body);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update source");
    }
  }

  return (
    <Box>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
        <Button variant="outlined" startIcon={<LinkIcon />} onClick={() => setOpen((value) => !value)}>
          {open ? "Hide sync" : "Sync calendars"}
        </Button>
        <Button variant="outlined" startIcon={<SyncIcon />} onClick={handleSyncAll} disabled={syncing || !sources.length}>
          Sync now
        </Button>
        {autoStatus ? (
          <Chip
            size="small"
            color={autoStatus.running ? "success" : "default"}
            label={autoStatus.running ? `Auto-sync on (tick ${autoStatus.tick_seconds}s)` : "Auto-sync idle"}
          />
        ) : null}
      </Stack>

      <Collapse in={open}>
        <Box
          sx={{
            mt: 2,
            p: 2,
            border: 1,
            borderColor: "divider",
            borderRadius: 1,
            display: "grid",
            gap: 1.5,
          }}
        >
          <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" useFlexGap spacing={1}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              Connected calendars
            </Typography>
            <Button size="small" variant="contained" onClick={() => setConnectOpen(true)}>
              Connect calendar
            </Button>
          </Stack>

          <Typography variant="body2" color="text.secondary">
            Google Calendar needs OAuth or a secret iCal URL. Gmail app passwords only work for email, not Calendar.
            CalDAV (iCloud, Nextcloud) still uses app passwords.
          </Typography>

          {error ? <Alert severity="error">{error}</Alert> : null}
          {status ? <Alert severity="success">{status}</Alert> : null}

          {loading ? (
            <Typography variant="body2" color="text.secondary">
              Loading sources…
            </Typography>
          ) : !sources.length ? (
            <Typography variant="body2" color="text.secondary">
              No external calendars connected yet. Use Connect with Google, a secret iCal URL, or CalDAV (iCloud /
              Nextcloud).
            </Typography>
          ) : (
            <Stack spacing={1}>
              {sources.map((source) => (
                <Box
                  key={source.id}
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    gap: 1,
                    flexWrap: "wrap",
                    py: 1,
                    borderBottom: 1,
                    borderColor: "divider",
                  }}
                >
                  <Box sx={{ minWidth: 0, flex: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                      <Typography sx={{ fontWeight: 600 }}>{source.name}</Typography>
                      <Chip size="small" label={source.provider} />
                      <Chip size="small" variant="outlined" label={source.sync_direction} />
                      {source.auto_sync ? (
                        <Chip size="small" color="info" label={`every ${source.sync_interval_minutes}m`} />
                      ) : (
                        <Chip size="small" label="manual" />
                      )}
                      {source.last_sync_ok === true ? <Chip size="small" color="success" label="OK" /> : null}
                      {source.last_sync_ok === false ? <Chip size="small" color="error" label="Error" /> : null}
                    </Stack>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, wordBreak: "break-all" }}>
                      {source.url || "(auto URL)"}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      {source.last_sync_at
                        ? `Last sync: ${new Date(source.last_sync_at).toLocaleString()}${
                            source.last_sync_message ? ` · ${source.last_sync_message}` : ""
                          }`
                        : "Not synced yet"}
                    </Typography>
                    {source.last_sync_ok === false && source.provider === "google" ? (
                      <Box sx={{ mt: 1, display: "grid", gap: 1 }}>
                        <Button size="small" variant="contained" onClick={() => void connectGoogleOAuth()}>
                          Connect with Google
                        </Button>
                        {icsRepairId === source.id ? (
                          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                            <TextField
                              size="small"
                              label="Secret iCal URL"
                              value={icsRepairUrl}
                              onChange={(e) => setIcsRepairUrl(e.target.value)}
                              sx={{ minWidth: 240, flex: 1 }}
                            />
                            <Button size="small" onClick={() => void repairWithIcs(source.id)} disabled={saving}>
                              Use ICS
                            </Button>
                          </Stack>
                        ) : (
                          <Button size="small" onClick={() => { setIcsRepairId(source.id); setIcsRepairUrl(""); }}>
                            Or paste secret ICS URL
                          </Button>
                        )}
                      </Box>
                    ) : null}
                    {source.auto_sync && source.next_sync_at ? (
                      <Typography variant="caption" color="text.secondary" display="block">
                        Next auto-sync: {new Date(source.next_sync_at).toLocaleString()}
                      </Typography>
                    ) : null}
                    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                      <FormControlLabel
                        control={
                          <Checkbox
                            size="small"
                            checked={Boolean(source.auto_sync)}
                            onChange={(e) => void patchSource(source.id, { auto_sync: e.target.checked })}
                          />
                        }
                        label="Auto-sync"
                      />
                      <FormControl size="small" sx={{ minWidth: 140 }}>
                        <InputLabel id={`interval-${source.id}`}>Interval</InputLabel>
                        <Select
                          labelId={`interval-${source.id}`}
                          label="Interval"
                          value={source.sync_interval_minutes || 15}
                          onChange={(e) =>
                            void patchSource(source.id, { sync_interval_minutes: Number(e.target.value) })
                          }
                        >
                          {INTERVAL_OPTIONS.map((mins) => (
                            <MenuItem key={mins} value={mins}>
                              {mins < 60 ? `${mins} min` : `${mins / 60} hr`}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Stack>
                  </Box>
                  <Stack direction="row" spacing={1}>
                    <Button size="small" onClick={() => handleSyncOne(source.id)} disabled={syncing}>
                      Sync
                    </Button>
                    <Button size="small" color="error" onClick={() => handleRemove(source)}>
                      Remove
                    </Button>
                  </Stack>
                </Box>
              ))}
            </Stack>
          )}
        </Box>
      </Collapse>

      <Dialog open={connectOpen} onClose={() => setConnectOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Connect calendar</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <FormControl fullWidth>
            <InputLabel id="calendar-provider-label">Provider</InputLabel>
            <Select
              labelId="calendar-provider-label"
              label="Provider"
              value={presetId}
              onChange={(event) => applyPreset(String(event.target.value))}
            >
              {providers.map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {item.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {preset ? (
            <Typography variant="body2" color="text.secondary">
              {preset.help}
            </Typography>
          ) : null}
          <TextField label="Display name" value={name} onChange={(e) => setName(e.target.value)} />
          <TextField
            label={preset?.provider === "ics" || presetId === "google-ics" ? "ICS feed URL" : "CalDAV URL"}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={preset?.url_hint}
            helperText={
              preset?.provider === "google"
                ? "Leave blank for OAuth. Or paste a secret iCal URL ending in .ics for pull-only."
                : undefined
            }
          />
          {preset?.provider === "google" ? (
            <Button variant="contained" onClick={() => void connectGoogleOAuth()}>
              Connect with Google
            </Button>
          ) : null}
          {preset?.provider !== "ics" && preset?.provider !== "google" ? (
            <>
              <TextField
                label="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
              <TextField
                label="Password / app password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
              />
              <TextField
                label="Calendar name (optional)"
                value={calendarName}
                onChange={(e) => setCalendarName(e.target.value)}
                helperText="If the account has multiple calendars, match by display name."
              />
              <FormControl fullWidth>
                <InputLabel id="sync-direction-label">Sync direction</InputLabel>
                <Select
                  labelId="sync-direction-label"
                  label="Sync direction"
                  value={syncDirection}
                  onChange={(event) => setSyncDirection(String(event.target.value))}
                >
                  {(preset?.sync_modes || ["pull"]).map((mode) => (
                    <MenuItem key={mode} value={mode}>
                      {mode}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={pushLocal}
                    onChange={(e) => setPushLocal(e.target.checked)}
                    disabled={syncDirection === "pull"}
                  />
                }
                label="Push new local Keprix events to this calendar (2-way)"
              />
            </>
          ) : null}
          <FormControlLabel
            control={<Checkbox checked={autoSync} onChange={(e) => setAutoSync(e.target.checked)} />}
            label="Enable automatic resync on an interval"
          />
          <FormControl fullWidth disabled={!autoSync}>
            <InputLabel id="connect-interval-label">Resync interval</InputLabel>
            <Select
              labelId="connect-interval-label"
              label="Resync interval"
              value={intervalMinutes}
              onChange={(e) => setIntervalMinutes(Number(e.target.value))}
            >
              {INTERVAL_OPTIONS.map((mins) => (
                <MenuItem key={mins} value={mins}>
                  {mins < 60 ? `Every ${mins} minutes` : `Every ${mins / 60} hours`}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConnectOpen(false)}>Cancel</Button>
          {preset?.provider === "google" && !url.trim() ? null : (
            <Button variant="contained" onClick={handleConnect} disabled={saving || !name.trim()}>
              Connect
            </Button>
          )}
        </DialogActions>
      </Dialog>

      <Dialog open={googleModalOpen} onClose={() => setGoogleModalOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Google Calendar OAuth credentials</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Create an OAuth client (Web application) in Google Cloud Console, enable Calendar API, then paste the
            Client ID and Client Secret. Add this exact Authorized redirect URI:
          </Typography>
          <TextField
            label="Authorized redirect URI (copy into Google Cloud)"
            value={googleConfig?.redirect_uri || "http://127.0.0.1:9119/api/workspace/calendar/google/callback"}
            InputProps={{ readOnly: true }}
            onFocus={(e) => e.target.select()}
          />
          {googleConfig?.configured ? (
            <Alert severity="info">Saved client: {googleConfig.client_id_masked}. Enter a new secret to replace it.</Alert>
          ) : null}
          <TextField
            label="Client ID"
            value={googleClientId}
            onChange={(e) => setGoogleClientId(e.target.value)}
            placeholder="123456789-abc.apps.googleusercontent.com"
            autoComplete="off"
          />
          <TextField
            label="Client Secret"
            type="password"
            value={googleClientSecret}
            onChange={(e) => setGoogleClientSecret(e.target.value)}
            autoComplete="new-password"
          />
          <Typography variant="caption" color="text.secondary">
            {googleConfig?.calendar_api_hint || "Enable Google Calendar API on the same Cloud project."}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setGoogleModalOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={googleSaving} onClick={() => void saveGoogleCredentialsAndConnect()}>
            Save and connect
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
