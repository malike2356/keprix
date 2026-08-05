"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";

type ComponentInspectorProps = {
  selector?: string | null;
  snippet?: string | null;
  meta?: Record<string, unknown> | null;
  skillMessage?: string | null;
  onLoadSkillMessage: () => Promise<void>;
};

export default function ComponentInspector({
  selector,
  snippet,
  meta,
  skillMessage,
  onLoadSkillMessage,
}: ComponentInspectorProps) {
  const [message, setMessage] = React.useState<string | null>(null);

  const copy = async (value: string, label: string) => {
    await navigator.clipboard.writeText(value);
    setMessage(`${label} copied.`);
  };

  return (
    <Stack spacing={1.5}>
      <Typography variant="subtitle1">Inspector</Typography>
      {message ? <Alert severity="info" onClose={() => setMessage(null)}>{message}</Alert> : null}
      <TextField label="Selector" value={selector || ""} size="small" InputProps={{ readOnly: true }} />
      <TextField
        label="Metadata"
        value={meta ? JSON.stringify(meta, null, 2) : ""}
        multiline
        minRows={4}
        InputProps={{ readOnly: true }}
      />
      <TextField
        label="HTML snippet"
        value={snippet || ""}
        multiline
        minRows={8}
        InputProps={{ readOnly: true }}
      />
      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
        <Button size="small" variant="outlined" disabled={!selector} onClick={() => void copy(selector || "", "Selector")}>
          Copy selector
        </Button>
        <Button size="small" variant="outlined" disabled={!snippet} onClick={() => void copy(snippet || "", "Snippet")}>
          Copy snippet
        </Button>
        <Button size="small" variant="contained" disabled={!selector} onClick={() => void onLoadSkillMessage()}>
          Improve with design skill
        </Button>
      </Stack>
      {skillMessage ? (
        <Box>
          <TextField
            label="Agent message"
            value={skillMessage}
            multiline
            minRows={8}
            fullWidth
            InputProps={{ readOnly: true }}
          />
          <Button sx={{ mt: 1 }} size="small" variant="text" onClick={() => void copy(skillMessage, "Agent message")}>
            Copy agent message
          </Button>
        </Box>
      ) : null}
    </Stack>
  );
}
