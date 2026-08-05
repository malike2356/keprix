"use client";

import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  createBrainShareLink,
  listBrainShareLinks,
  revokeBrainShareLink,
  sharePageUrl,
  type BrainShareLink,
  type ShareScope,
} from "@/lib/brain-share-api";

type Props = {
  open: boolean;
  onClose: () => void;
  workspaceId?: string;
};

const EXPIRY_OPTIONS: Array<{ label: string; days: number | null }> = [
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "Never", days: null },
];

const SCOPE_OPTIONS: Array<{ label: string; value: ShareScope }> = [
  { label: "All nodes", value: "all" },
  { label: "Memories only", value: "memories_only" },
  { label: "Skills only", value: "skills_only" },
];

function expiryLabel(link: BrainShareLink): string {
  if (!link.expires_at) return "never";
  const days = Math.max(1, Math.round((new Date(link.expires_at).getTime() - Date.now()) / 86_400_000));
  return `${days}d`;
}

export default function BrainShareModal({ open, onClose, workspaceId }: Props) {
  const [scope, setScope] = React.useState<ShareScope>("all");
  const [expiresInDays, setExpiresInDays] = React.useState<number | null>(7);
  const [password, setPassword] = React.useState("");
  const [links, setLinks] = React.useState<BrainShareLink[]>([]);
  const [latestUrl, setLatestUrl] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    const rows = await listBrainShareLinks(workspaceId);
    setLinks(rows);
  }, [workspaceId]);

  React.useEffect(() => {
    if (!open) return;
    setError(null);
    void refresh().catch(() => setLinks([]));
  }, [open, refresh]);

  const generate = async () => {
    setBusy(true);
    setError(null);
    try {
      const link = await createBrainShareLink({
        scope,
        expires_in_days: expiresInDays,
        password: password.trim() || null,
        workspaceId,
      });
      setLatestUrl(link.url || sharePageUrl(link.share_id));
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create share link");
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (shareId: string) => {
    setBusy(true);
    try {
      await revokeBrainShareLink(shareId, workspaceId);
      if (latestUrl?.includes(shareId)) setLatestUrl(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revoke share link");
    } finally {
      setBusy(false);
    }
  };

  const copyUrl = async (url: string) => {
    await navigator.clipboard.writeText(url).catch(() => undefined);
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Share your brain graph</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 0.5 }}>
          <TextField select label="Scope" size="small" value={scope} onChange={(event) => setScope(event.target.value as ShareScope)}>
            {SCOPE_OPTIONS.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Expires"
            size="small"
            value={expiresInDays === null ? "never" : String(expiresInDays)}
            onChange={(event) => {
              const value = event.target.value;
              setExpiresInDays(value === "never" ? null : Number(value));
            }}
          >
            {EXPIRY_OPTIONS.map((option) => (
              <MenuItem key={option.label} value={option.days === null ? "never" : String(option.days)}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Password (optional)"
            size="small"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <Button variant="contained" disabled={busy} onClick={() => void generate()}>
            Generate link
          </Button>
          {error ? (
            <Typography variant="body2" color="error">
              {error}
            </Typography>
          ) : null}
          {latestUrl ? (
            <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.5 }}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="body2" sx={{ flex: 1, wordBreak: "break-all" }}>
                  {latestUrl}
                </Typography>
                <IconButton size="small" aria-label="Copy link" onClick={() => void copyUrl(latestUrl)}>
                  <ContentCopyIcon fontSize="small" />
                </IconButton>
                <IconButton size="small" aria-label="Open link" href={latestUrl} target="_blank" rel="noreferrer">
                  <OpenInNewIcon fontSize="small" />
                </IconButton>
              </Stack>
            </Box>
          ) : null}
          <Typography variant="subtitle2">Active links</Typography>
          {links.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No active share links yet.
            </Typography>
          ) : (
            <Stack spacing={1}>
              {links.map((link) => {
                const url = link.url || sharePageUrl(link.share_id);
                return (
                  <Stack key={link.share_id} direction="row" spacing={1} alignItems="center">
                    <Typography variant="body2" sx={{ flex: 1 }}>
                      {link.share_id} · {expiryLabel(link)} · accessed {link.access_count} times
                    </Typography>
                    <Button size="small" color="error" disabled={busy} onClick={() => void revoke(link.share_id)}>
                      Revoke
                    </Button>
                    <IconButton size="small" aria-label="Copy link" onClick={() => void copyUrl(url)}>
                      <ContentCopyIcon fontSize="small" />
                    </IconButton>
                  </Stack>
                );
              })}
            </Stack>
          )}
        </Stack>
      </DialogContent>
    </Dialog>
  );
}
