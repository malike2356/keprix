"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import {
  fetchAgentAppEvalLast,
  runAgentAppEvals,
  type AgentAppEvalResult,
} from "@/lib/agent-apps-api";

type Props = {
  appName: string;
  evalSuite?: string | null;
};

export default function AgentAppEvalsPanel({ appName, evalSuite }: Props) {
  const { data, mutate, isLoading } = useSWR(["agent-app-eval-last", appName], () =>
    fetchAgentAppEvalLast(appName),
  );
  const [result, setResult] = React.useState<AgentAppEvalResult | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const last = result ?? data?.last?.result ?? null;
  const lastRanAt = data?.last?.ran_at;

  const onRun = async () => {
    setBusy(true);
    setError(null);
    try {
      const payload = await runAgentAppEvals(appName);
      setResult(payload.result);
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eval run failed");
    } finally {
      setBusy(false);
    }
  };

  if (!evalSuite) {
    return (
      <Typography variant="body2" color="text.secondary">
        This app does not define an eval suite in its manifest.
      </Typography>
    );
  }

  return (
    <Box>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <Typography variant="subtitle1">Eval suite</Typography>
        <Chip size="small" label={evalSuite} variant="outlined" />
        <Button variant="contained" size="small" disabled={busy} onClick={onRun}>
          {busy ? "Running..." : "Run eval suite"}
        </Button>
        <Button
          size="small"
          component={Link}
          href={`/evals?suite=${encodeURIComponent(appName)}`}
        >
          Open global evals
        </Button>
      </Stack>

      {isLoading ? <Typography variant="body2">Loading last result...</Typography> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}

      {last ? (
        <Box>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
            <Chip
              size="small"
              color={last.success ? "success" : "error"}
              label={last.success ? "Passed" : "Failed"}
            />
            <Typography variant="body2">
              {last.passed}/{last.total} cases passed
            </Typography>
            {lastRanAt ? (
              <Typography variant="caption" color="text.secondary">
                Last run {new Date(lastRanAt).toLocaleString()}
              </Typography>
            ) : null}
          </Stack>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Case</TableCell>
                <TableCell>Result</TableCell>
                <TableCell>Output preview</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {last.cases.map((item) => (
                <TableRow key={item.name}>
                  <TableCell>{item.name}</TableCell>
                  <TableCell>
                    <Chip size="small" color={item.passed ? "success" : "error"} label={item.passed ? "pass" : "fail"} />
                  </TableCell>
                  <TableCell sx={{ maxWidth: 360 }}>
                    <Typography variant="body2" noWrap title={item.output}>
                      {item.output}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      ) : (
        <Typography variant="body2" color="text.secondary">
          No eval results yet. Run the suite to validate this app.
        </Typography>
      )}
    </Box>
  );
}
