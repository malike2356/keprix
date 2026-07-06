"use client";

import StopIcon from "@mui/icons-material/Stop";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import { alpha, keyframes } from "@mui/material/styles";
import type { AvailableModel } from "@/lib/workspace-api";

const pulse = keyframes`
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.45; transform: scale(0.85); }
`;

type ChatStatusBarProps = {
  model?: AvailableModel | null;
  models?: AvailableModel[];
  modelId?: string;
  onModelChange?: (modelId: string) => void;
  isStreaming?: boolean;
  onStop?: () => void;
  sessionCount?: number;
  connected?: boolean;
  version?: string;
};

export default function ChatStatusBar({
  model,
  models = [],
  modelId,
  onModelChange,
  isStreaming = false,
  onStop,
  sessionCount = 0,
  connected = true,
  version = "0.1.0",
}: ChatStatusBarProps) {
  const activeModel = model || models.find((item) => item.id === modelId) || null;

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1.5,
        px: 2,
        minHeight: 32,
        borderTop: 1,
        borderColor: "divider",
        bgcolor: (theme) => alpha(theme.palette.common.black, theme.palette.mode === "dark" ? 0.15 : 0.04),
        color: "text.secondary",
      }}
    >
      <Box
        sx={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          bgcolor: connected ? "success.main" : "error.main",
          animation: isStreaming ? `${pulse} 1.2s ease-in-out infinite` : "none",
        }}
      />
      {models.length > 0 && onModelChange ? (
        <Select
          size="small"
          variant="standard"
          value={modelId || activeModel?.id || ""}
          onChange={(event) => onModelChange(String(event.target.value))}
          disableUnderline
          sx={{ fontSize: "0.8rem", minWidth: 160 }}
        >
          {models.map((item) => (
            <MenuItem key={item.id} value={item.id}>
              {item.provider} / {item.name}
            </MenuItem>
          ))}
        </Select>
      ) : activeModel ? (
        <>
          <Chip size="small" label={activeModel.provider} variant="outlined" />
          <Typography variant="caption">{activeModel.name}</Typography>
        </>
      ) : (
        <Typography variant="caption">{connected ? "Connected" : "Reconnecting"}</Typography>
      )}
      <Box sx={{ flex: 1 }} />
      {isStreaming ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="caption" sx={{ fontWeight: 600 }}>
            Responding...
          </Typography>
          {onStop ? (
            <Button size="small" color="inherit" startIcon={<StopIcon />} onClick={onStop}>
              Stop
            </Button>
          ) : null}
        </Box>
      ) : (
        <>
          <Typography variant="caption">Sessions: {sessionCount}</Typography>
          <Typography variant="caption">| keprix v{version}</Typography>
        </>
      )}
    </Box>
  );
}
