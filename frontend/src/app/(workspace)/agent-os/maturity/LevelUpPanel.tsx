"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

type Action = { id: string; title: string; leverage: string; kind: string; action_url?: string | null; completed: boolean; instructions_md: string };
type Plan = { plan_id: string; actions: Action[]; estimated_score_delta: number };

export default function LevelUpPanel({ auditId, workspacePath }: { auditId: string; workspacePath?: string }) {
  const [plan, setPlan] = React.useState<Plan | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const parse = async <T,>(response: Response, fallback: string): Promise<T> => {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(parseApiErrorMessage(payload, fallback));
    return payload as T;
  };

  const generate = async () => {
    setError(null);
    const payload = await parse<{ plan: Plan }>(
      await ceApi("/api/agent-os/level-up/generate", {
        method: "POST",
        body: JSON.stringify({ audit_id: auditId, workspace_path: workspacePath || undefined }),
      }),
      "Could not generate level-up plan",
    );
    setPlan(payload.plan);
  };

  const complete = async (action: Action) => {
    if (!plan) return;
    const payload = await parse<{ plan: Plan }>(
      await ceApi(`/api/agent-os/level-up/${encodeURIComponent(plan.plan_id)}/actions/${encodeURIComponent(action.id)}/complete`, { method: "POST" }),
      "Could not complete action",
    );
    setPlan(payload.plan);
  };

  const applyStubs = async () => {
    if (!plan) return;
    const payload = await parse<{ plan: Plan; written: string[] }>(
      await ceApi(`/api/agent-os/level-up/${encodeURIComponent(plan.plan_id)}/apply-safe-stubs`, { method: "POST" }),
      "Could not apply stubs",
    );
    setPlan(payload.plan);
    setMessage(`Created ${payload.written.length} safe stub file(s).`);
  };

  const completed = plan?.actions.filter((action) => action.completed).length || 0;
  const total = plan?.actions.length || 0;

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.5}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="subtitle1">Level up</Typography>
            {plan ? <Chip label={`+${plan.estimated_score_delta} est.`} /> : null}
          </Stack>
          {error ? <Alert severity="error">{error}</Alert> : null}
          {message ? <Alert severity="info" onClose={() => setMessage(null)}>{message}</Alert> : null}
          {!plan ? (
            <Button variant="contained" onClick={() => void generate()}>Generate plan</Button>
          ) : (
            <>
              <LinearProgress variant="determinate" value={total ? (completed / total) * 100 : 0} />
              <Button variant="outlined" onClick={() => void applyStubs()}>Apply safe stubs</Button>
              {plan.actions.map((action) => (
                <Box key={action.id} sx={{ borderTop: "1px solid", borderColor: "divider", pt: 1 }}>
                  <Stack direction="row" justifyContent="space-between" spacing={1}>
                    <Typography variant="body2">{action.title}</Typography>
                    <Chip size="small" label={action.leverage} />
                  </Stack>
                  <Typography variant="caption" color="text.secondary">{action.instructions_md}</Typography>
                  <Button size="small" disabled={action.completed} onClick={() => void complete(action)} sx={{ mt: 0.5 }}>
                    {action.completed ? "Done" : "Mark done"}
                  </Button>
                </Box>
              ))}
            </>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
