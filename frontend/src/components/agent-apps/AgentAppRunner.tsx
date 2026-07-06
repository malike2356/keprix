"use client";

import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { fetchAgentTraces, runAgentApp } from "@/lib/agent-apps-api";

type Props = {
  appName: string;
};

export default function AgentAppRunner({ appName }: Props) {
  const [input, setInput] = React.useState("world");
  const [output, setOutput] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const { data: traces, mutate } = useSWR(["agent-traces", appName], () => fetchAgentTraces(appName));

  const onRun = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await runAgentApp(appName, { input });
      setOutput(result.result.output ?? JSON.stringify(result.result));
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Run {appName}
        </Typography>
        <Box sx={{ display: "grid", gap: 2 }}>
          <TextField label="Input" value={input} onChange={(e) => setInput(e.target.value)} size="small" />
          <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={onRun} disabled={busy}>
            {busy ? "Running..." : "Run via web runner"}
          </Button>
        </Box>
        {error ? (
          <Typography color="error" variant="body2" sx={{ mt: 2 }}>
            {error}
          </Typography>
        ) : null}
        {output ? (
          <Typography variant="body2" sx={{ mt: 2, whiteSpace: "pre-wrap" }}>
            {output}
          </Typography>
        ) : null}
        {traces?.traces?.length ? (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2">Lifecycle traces</Typography>
            <Typography variant="caption" component="pre" sx={{ whiteSpace: "pre-wrap" }}>
              {JSON.stringify(traces.traces, null, 2)}
            </Typography>
          </Box>
        ) : null}
      </CardContent>
    </Card>
  );
}
