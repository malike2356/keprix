"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Grid from "@mui/material/Grid2";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import {
  IconApi,
  IconBrandDiscord,
  IconBrandTelegram,
  IconEye,
  IconEyeOff,
} from "@tabler/icons-react";
import * as React from "react";
import useSWR from "swr";
import ChannelsAdminTable from "@/components/admin/ChannelsAdminTable";
import BlankCard from "@/components/cards/BlankCard";
import PageContainer from "@/components/shared/PageContainer";
import {
  createApiKey,
  fetchApiKeys,
  fetchChannelsOverview,
  fetchTelegramChannelConfig,
  revokeApiKey,
  saveDiscordChannel,
  saveTelegramChannel,
  testDiscordChannel,
  testTelegramChannel,
  type ChannelOverview,
} from "@/lib/admin-workspace-api";

function statusChip(status: string) {
  if (status === "connected" || status === "active") return <Chip size="small" color="success" label={status} />;
  if (status === "not_configured") return <Chip size="small" label="Not configured" />;
  return <Chip size="small" color="warning" label={status} />;
}

function ChannelCard({
  channel,
  onConfigure,
  onTest,
  onManageKeys,
}: {
  channel: ChannelOverview;
  onConfigure?: () => void;
  onTest?: () => void;
  onManageKeys?: () => void;
}) {
  const icon =
    channel.id === "telegram" ? (
      <IconBrandTelegram size={22} stroke={1.75} />
    ) : channel.id === "discord" ? (
      <IconBrandDiscord size={22} stroke={1.75} />
    ) : (
      <IconApi size={22} stroke={1.75} />
    );

  return (
    <BlankCard sx={{ width: "100%", height: "100%", display: "flex", flexDirection: "column" }}>
      <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 1.5, flex: 1 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {icon}
          <Typography variant="h6">{channel.name}</Typography>
        </Box>
        {statusChip(channel.status)}
        <Box sx={{ minHeight: 52, display: "flex", flexDirection: "column", gap: 0.5, flex: 1 }}>
          {channel.bot_username ? (
            <Typography variant="body2" color="text.secondary">
              Bot: {channel.bot_username}
            </Typography>
          ) : null}
          {channel.message_count !== undefined ? (
            <Typography variant="body2" color="text.secondary">
              Messages: {channel.message_count}
            </Typography>
          ) : null}
          {channel.endpoint ? (
            <Typography variant="body2" color="text.secondary" noWrap title={channel.endpoint}>
              Endpoint: {channel.endpoint}
            </Typography>
          ) : null}
          {channel.active_keys !== undefined ? (
            <Typography variant="body2" color="text.secondary">
              Keys: {channel.active_keys} active
            </Typography>
          ) : null}
        </Box>
        <Box sx={{ display: "flex", gap: 1, mt: "auto", flexWrap: "wrap" }}>
          {onConfigure ? (
            <Button size="small" variant="outlined" onClick={onConfigure}>
              {channel.status === "not_configured" ? "Connect" : "Configure"}
            </Button>
          ) : null}
          {onTest ? (
            <Button size="small" onClick={onTest}>
              Test
            </Button>
          ) : null}
          {onManageKeys ? (
            <Button size="small" href="/dashboard/keys">
              Manage keys
            </Button>
          ) : null}
        </Box>
      </Box>
    </BlankCard>
  );
}

export default function AdminChannelsPage() {
  const { data, mutate } = useSWR("channels-overview", fetchChannelsOverview);
  const { data: keysData, mutate: mutateKeys } = useSWR("channel-keys", fetchApiKeys);
  const [telegramOpen, setTelegramOpen] = React.useState(false);
  const [discordOpen, setDiscordOpen] = React.useState(false);
  const [createKeyOpen, setCreateKeyOpen] = React.useState(false);
  const [showToken, setShowToken] = React.useState(false);
  const [telegramToken, setTelegramToken] = React.useState("");
  const [telegramWebhook, setTelegramWebhook] = React.useState("");
  const [discordToken, setDiscordToken] = React.useState("");
  const [discordAppId, setDiscordAppId] = React.useState("");
  const [discordGuildId, setDiscordGuildId] = React.useState("");
  const [testMessage, setTestMessage] = React.useState<string | null>(null);
  const [newKeyName, setNewKeyName] = React.useState("");
  const [createdSecret, setCreatedSecret] = React.useState<string | null>(null);

  const channels = data?.channels || [];
  const telegram = channels.find((item) => item.id === "telegram");
  const discord = channels.find((item) => item.id === "discord");
  const rest = channels.find((item) => item.id === "rest");

  return (
    <PageContainer title="Channels" description="Messaging and API channel connections." padded={false}>
      <Grid container spacing={2} alignItems="stretch">
        <Grid size={{ xs: 12, md: 4 }} sx={{ display: "flex" }}>
          <ChannelCard
            channel={telegram || { id: "telegram", name: "Telegram", status: "not_configured" }}
            onConfigure={() => {
              void fetchTelegramChannelConfig()
                .then((config) => setTelegramWebhook(config.webhook_url))
                .catch(() => setTelegramWebhook(""));
              setTelegramOpen(true);
            }}
            onTest={() => {
              void testTelegramChannel().then((result) => setTestMessage(result.message));
            }}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }} sx={{ display: "flex" }}>
          <ChannelCard
            channel={discord || { id: "discord", name: "Discord", status: "not_configured" }}
            onConfigure={() => setDiscordOpen(true)}
            onTest={() => {
              void testDiscordChannel().then((result) => setTestMessage(result.message));
            }}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }} sx={{ display: "flex" }}>
          <ChannelCard
            channel={rest || { id: "rest", name: "REST API", status: "active", endpoint: ":3333/api", active_keys: 0 }}
            onManageKeys={() => setCreateKeyOpen(true)}
          />
        </Grid>
      </Grid>

      {testMessage ? (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          {testMessage}
        </Typography>
      ) : null}

      <BlankCard>
        <Box sx={{ p: 2 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
            <Typography variant="h6">REST API keys</Typography>
            <Button variant="contained" onClick={() => setCreateKeyOpen(true)}>
              Create new key
            </Button>
          </Box>
          {(keysData?.keys || []).map((key) => (
            <Box key={key.id} sx={{ display: "flex", justifyContent: "space-between", py: 1, borderBottom: 1, borderColor: "divider" }}>
              <Box>
                <Typography variant="body2">{key.name}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {key.key_prefix}... | created {key.created_at}
                </Typography>
              </Box>
              <Button color="error" size="small" onClick={() => void revokeApiKey(key.id).then(() => mutateKeys())}>
                Revoke
              </Button>
            </Box>
          ))}
          {!keysData?.keys?.length ? (
            <Typography variant="body2" color="text.secondary">
              No API keys yet.
            </Typography>
          ) : null}
        </Box>
      </BlankCard>

      <ChannelsAdminTable />

      <Dialog open={telegramOpen} onClose={() => setTelegramOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Configure Telegram</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <TextField
            label="Bot token"
            type={showToken ? "text" : "password"}
            value={telegramToken}
            onChange={(event) => setTelegramToken(event.target.value)}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowToken((value) => !value)}>
                    {showToken ? <IconEyeOff size={18} stroke={1.75} /> : <IconEye size={18} stroke={1.75} />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
          <TextField label="Webhook URL" value={telegramWebhook || "Loading..."} InputProps={{ readOnly: true }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => void testTelegramChannel().then((result) => setTestMessage(result.message))}>Test connection</Button>
          <Button
            variant="contained"
            onClick={() => {
              void saveTelegramChannel(telegramToken).then(() => {
                setTelegramOpen(false);
                void mutate();
              });
            }}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={discordOpen} onClose={() => setDiscordOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Configure Discord</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <TextField label="Bot token" type="password" value={discordToken} onChange={(event) => setDiscordToken(event.target.value)} />
          <TextField label="Application ID" value={discordAppId} onChange={(event) => setDiscordAppId(event.target.value)} />
          <TextField label="Server (Guild) ID" value={discordGuildId} onChange={(event) => setDiscordGuildId(event.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => void testDiscordChannel().then((result) => setTestMessage(result.message))}>Test connection</Button>
          <Button
            variant="contained"
            onClick={() => {
              void saveDiscordChannel({
                bot_token: discordToken,
                application_id: discordAppId,
                guild_id: discordGuildId,
              }).then(() => {
                setDiscordOpen(false);
                void mutate();
              });
            }}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={createKeyOpen} onClose={() => setCreateKeyOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create API key</DialogTitle>
        <DialogContent>
          {createdSecret ? (
            <Box sx={{ p: 2, border: 1, borderColor: "warning.main", borderRadius: 1 }}>
              <Typography variant="body2" color="warning.main" sx={{ mb: 1 }}>
                This key will not be shown again. Copy it now.
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                {createdSecret}
              </Typography>
            </Box>
          ) : (
            <TextField
              fullWidth
              label="Key name"
              value={newKeyName}
              onChange={(event) => setNewKeyName(event.target.value)}
              sx={{ mt: 1 }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateKeyOpen(false)}>Close</Button>
          {!createdSecret ? (
            <Button
              variant="contained"
              disabled={!newKeyName.trim()}
              onClick={() => {
                void createApiKey({ name: newKeyName.trim(), expiry: "none", scopes: ["read", "write"] }).then((created) => {
                  setCreatedSecret(created.secret);
                  void mutateKeys();
                });
              }}
            >
              Create
            </Button>
          ) : null}
        </DialogActions>
      </Dialog>
    </PageContainer>
  );
}
