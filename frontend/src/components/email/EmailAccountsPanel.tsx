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
import LinkIcon from "@mui/icons-material/Link";
import * as React from "react";
import {
  createEmailAccount,
  deleteEmailAccount,
  fetchEmailProviders,
  fetchGmailAuthUrl,
  testEmailAccount,
  updateEmailAccount,
  type EmailAccount,
  type EmailProviderPreset,
} from "@/lib/email-api";

const INTERVAL_OPTIONS = [
  { label: "1 min", value: 60 },
  { label: "5 min", value: 300 },
  { label: "15 min", value: 900 },
  { label: "30 min", value: 1800 },
  { label: "1 hour", value: 3600 },
];

type Props = {
  accounts: EmailAccount[];
  onChanged: () => void;
};

export default function EmailAccountsPanel({ accounts, onChanged }: Props) {
  const [open, setOpen] = React.useState(false);
  const [connectOpen, setConnectOpen] = React.useState(false);
  const [providers, setProviders] = React.useState<EmailProviderPreset[]>([]);
  const [gmailOauth, setGmailOauth] = React.useState(false);
  const [presetId, setPresetId] = React.useState("gmail");
  const [label, setLabel] = React.useState("Gmail");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [imapHost, setImapHost] = React.useState("imap.gmail.com");
  const [smtpHost, setSmtpHost] = React.useState("smtp.gmail.com");
  const [imapPort, setImapPort] = React.useState(993);
  const [smtpPort, setSmtpPort] = React.useState(587);
  const [intervalSec, setIntervalSec] = React.useState(300);
  const [useStarttls, setUseStarttls] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [status, setStatus] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);

  const preset = providers.find((item) => item.id === presetId) || providers[0];

  React.useEffect(() => {
    void fetchEmailProviders()
      .then((data) => {
        setProviders(data.items);
        setGmailOauth(Boolean(data.gmail_oauth_configured));
        if (data.items[0]) {
          applyPreset(data.items[0].id, data.items);
        }
      })
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyPreset(nextId: string, list = providers) {
    setPresetId(nextId);
    const next = list.find((item) => item.id === nextId);
    if (!next) return;
    setLabel(next.label);
    setImapHost(next.imap_host);
    setSmtpHost(next.smtp_host);
    setImapPort(next.imap_port);
    setSmtpPort(next.smtp_port);
    setUseStarttls(next.use_starttls);
  }

  async function handleConnect() {
    if (!email.trim() || !password.trim()) {
      setError("Email and password (or app password) are required");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createEmailAccount({
        label: label.trim() || email.trim(),
        email_address: email.trim(),
        username: email.trim(),
        password: password,
        imap_host: imapHost.trim(),
        imap_port: imapPort,
        smtp_host: smtpHost.trim(),
        smtp_port: smtpPort,
        use_tls: true,
        use_starttls: useStarttls,
        poll_interval_seconds: intervalSec,
      });
      setConnectOpen(false);
      setPassword("");
      setStatus(`Connected ${email.trim()}. Auto-sync every ${Math.round(intervalSec / 60)} min.`);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect account");
    } finally {
      setSaving(false);
    }
  }

  async function handleGmailOauth() {
    try {
      const { auth_url: authUrl } = await fetchGmailAuthUrl();
      window.location.href = authUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gmail OAuth unavailable");
    }
  }

  async function patchInterval(accountId: string, seconds: number) {
    try {
      await updateEmailAccount(accountId, { poll_interval_seconds: seconds });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update interval");
    }
  }

  async function handleTest(accountId: string) {
    try {
      await testEmailAccount(accountId);
      setStatus("Connection test OK");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection test failed");
    }
  }

  async function handleRemove(account: EmailAccount) {
    if (!window.confirm(`Remove ${account.email_address}?`)) return;
    try {
      await deleteEmailAccount(account.id);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove account");
    }
  }

  return (
    <Box sx={{ mb: 2 }}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Button variant="outlined" startIcon={<LinkIcon />} onClick={() => setOpen((v) => !v)}>
          {open ? "Hide accounts" : "Connect email"}
        </Button>
        <Button size="small" variant="contained" onClick={() => setConnectOpen(true)}>
          Add account
        </Button>
      </Stack>

      <Collapse in={open || accounts.length > 0}>
        <Box sx={{ mt: 1.5, p: 2, border: 1, borderColor: "divider", borderRadius: 1, display: "grid", gap: 1.5 }}>
          <Typography variant="body2" color="text.secondary">
            Sync Gmail, Outlook, Yahoo, or any IMAP mailbox on a configurable interval. Compose and send uses the
            account SMTP settings.
          </Typography>
          {error ? <Alert severity="error">{error}</Alert> : null}
          {status ? <Alert severity="success">{status}</Alert> : null}
          {!accounts.length ? (
            <Typography variant="body2" color="text.secondary">
              No accounts yet. Add Gmail with an app password, or another IMAP provider.
            </Typography>
          ) : (
            <Stack spacing={1}>
              {accounts.map((account) => (
                <Box
                  key={account.id}
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 1,
                    flexWrap: "wrap",
                    py: 1,
                    borderBottom: 1,
                    borderColor: "divider",
                  }}
                >
                  <Box sx={{ minWidth: 0, flex: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                      <Typography sx={{ fontWeight: 600 }}>{account.label}</Typography>
                      <Chip size="small" label={account.email_address} />
                      {account.oauth_provider ? <Chip size="small" color="info" label={account.oauth_provider} /> : null}
                      <Chip
                        size="small"
                        variant="outlined"
                        label={`every ${Math.max(1, Math.round((account.poll_interval_seconds || 300) / 60))}m`}
                      />
                    </Stack>
                    <Typography variant="caption" color="text.secondary" display="block">
                      {account.last_polled_at
                        ? `Last sync: ${new Date(account.last_polled_at).toLocaleString()}`
                        : "Not synced yet"}
                      {account.next_sync_at ? ` · Next: ${new Date(account.next_sync_at).toLocaleString()}` : ""}
                    </Typography>
                    <FormControl size="small" sx={{ mt: 1, minWidth: 140 }}>
                      <InputLabel id={`email-int-${account.id}`}>Interval</InputLabel>
                      <Select
                        labelId={`email-int-${account.id}`}
                        label="Interval"
                        value={account.poll_interval_seconds || 300}
                        onChange={(e) => void patchInterval(account.id, Number(e.target.value))}
                      >
                        {INTERVAL_OPTIONS.map((opt) => (
                          <MenuItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Box>
                  <Stack direction="row" spacing={1}>
                    <Button size="small" onClick={() => void handleTest(account.id)}>
                      Test
                    </Button>
                    <Button size="small" color="error" onClick={() => void handleRemove(account)}>
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
        <DialogTitle>Connect email account</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <FormControl fullWidth>
            <InputLabel id="email-provider-label">Provider</InputLabel>
            <Select
              labelId="email-provider-label"
              label="Provider"
              value={presetId}
              onChange={(e) => applyPreset(String(e.target.value))}
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
          {gmailOauth && presetId === "gmail" ? (
            <Button variant="outlined" onClick={() => void handleGmailOauth()}>
              Connect Gmail with Google OAuth
            </Button>
          ) : null}
          <TextField label="Display name" value={label} onChange={(e) => setLabel(e.target.value)} />
          <TextField label="Email address" value={email} onChange={(e) => setEmail(e.target.value)} />
          <TextField
            label="Password / app password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
          />
          <TextField label="IMAP host" value={imapHost} onChange={(e) => setImapHost(e.target.value)} />
          <TextField label="SMTP host" value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} />
          <Stack direction="row" spacing={1}>
            <TextField
              label="IMAP port"
              type="number"
              value={imapPort}
              onChange={(e) => setImapPort(Number(e.target.value))}
              sx={{ flex: 1 }}
            />
            <TextField
              label="SMTP port"
              type="number"
              value={smtpPort}
              onChange={(e) => setSmtpPort(Number(e.target.value))}
              sx={{ flex: 1 }}
            />
          </Stack>
          <FormControlLabel
            control={<Checkbox checked={useStarttls} onChange={(e) => setUseStarttls(e.target.checked)} />}
            label="SMTP STARTTLS"
          />
          <FormControl fullWidth>
            <InputLabel id="email-connect-interval">Resync interval</InputLabel>
            <Select
              labelId="email-connect-interval"
              label="Resync interval"
              value={intervalSec}
              onChange={(e) => setIntervalSec(Number(e.target.value))}
            >
              {INTERVAL_OPTIONS.map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>
                  Every {opt.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConnectOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => void handleConnect()} disabled={saving}>
            Connect
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
