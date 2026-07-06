"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import {
  enableAmbientMode,
  fetchRoomConfig,
  fetchRooms,
  patchRoomConfig,
} from "@/lib/messaging-api";

const CHANNELS = ["whatsapp", "telegram", "slack", "discord", "matrix", "signal"];

export default function MessagingSettingsPage() {
  const [roomId, setRoomId] = React.useState("group-1");
  const [channelType, setChannelType] = React.useState("whatsapp");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const { data: roomsData, mutate: mutateRooms } = useSWR("rooms", fetchRooms);
  const { data: config, mutate: mutateConfig } = useSWR(
    roomId ? ["room-config", roomId, channelType] : null,
    () => fetchRoomConfig(roomId, "default", channelType),
  );

  const ambientEnabled = config?.unmentioned_inbound === "room_event";

  const handleAmbientToggle = async (enabled: boolean) => {
    setError(null);
    try {
      if (enabled) {
        await enableAmbientMode(roomId, "default", channelType);
      } else {
        await patchRoomConfig(roomId, {
          unmentioned_inbound: "normal",
          visible_replies: "auto",
          channel_type: channelType,
        });
      }
      await mutateConfig();
      await mutateRooms();
      setMessage(enabled ? "Ambient monitoring enabled" : "Ambient monitoring disabled");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  };

  const handleAlwaysOnToggle = async (enabled: boolean) => {
    setError(null);
    try {
      await patchRoomConfig(roomId, { always_on: enabled, channel_type: channelType });
      await mutateConfig();
      setMessage(enabled ? "Always-on enabled" : "Always-on disabled");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  };

  return (
    <Box>
      <PageHeader
        title="Messaging rooms"
        description="Configure ambient monitoring for group channels."
      />
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Room selection</Typography>
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            <TextField label="Room ID" value={roomId} onChange={(event) => setRoomId(event.target.value)} />
            <FormControl sx={{ minWidth: 180 }}>
              <InputLabel id="channel-type-label">Channel</InputLabel>
              <Select
                labelId="channel-type-label"
                label="Channel"
                value={channelType}
                onChange={(event) => setChannelType(event.target.value)}
              >
                {CHANNELS.map((channel) => (
                  <MenuItem key={channel} value={channel}>{channel}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </CardContent>
      </Card>

      {config ? (
        <Card>
          <CardContent>
            <Tooltip title="In ambient mode, the agent listens to all messages but only replies when it has something useful to add.">
              <FormControlLabel
                control={<Switch checked={ambientEnabled} onChange={(event) => handleAmbientToggle(event.target.checked)} />}
                label="Ambient monitoring mode"
              />
            </Tooltip>
            <Box sx={{ mt: 2 }}>
              <Tooltip title="Not all channels support always-on delivery without mentions.">
                <span>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={Boolean(config.always_on)}
                        disabled={!config.supports_always_on}
                        onChange={(event) => handleAlwaysOnToggle(event.target.checked)}
                      />
                    }
                    label="Always-on"
                  />
                </span>
              </Tooltip>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Visible replies: {config.visible_replies}. History limit: {config.history_limit}.
            </Typography>
          </CardContent>
        </Card>
      ) : null}

      <Card sx={{ mt: 2 }}>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>Saved rooms</Typography>
          {(roomsData?.rooms ?? []).length === 0 ? (
            <Typography variant="body2">No room configs saved yet.</Typography>
          ) : (
            roomsData?.rooms.map((room) => (
              <Box key={room.room_id} sx={{ mb: 1 }}>
                <Button variant="text" onClick={() => { setRoomId(room.room_id); setChannelType(room.channel_type); }}>
                  {room.room_id} ({room.channel_type})
                </Button>
              </Box>
            ))
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
