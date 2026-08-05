"use client";

import TextField from "@mui/material/TextField";

export default function LiveSessionSelector({
  sessionId,
  onSessionId,
  compact = false,
}: {
  sessionId: string;
  onSessionId: (value: string) => void;
  compact?: boolean;
}) {
  return (
    <TextField
      size="small"
      hiddenLabel
      value={sessionId}
      onChange={(event) => onSessionId(event.target.value)}
      placeholder="Live session id"
      sx={{
        width: compact ? 132 : 180,
        "& .MuiOutlinedInput-root": {
          height: compact ? 30 : 36,
          typography: "caption",
          bgcolor: "transparent",
        },
        "& .MuiOutlinedInput-input": {
          py: 0.5,
          px: 1,
        },
      }}
    />
  );
}
