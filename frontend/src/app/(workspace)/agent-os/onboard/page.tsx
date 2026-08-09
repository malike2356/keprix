"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { AGENT_OS_HUB_HOME } from "@/components/agent-os/AgentOsSubnav";
import ErrorState from "@/components/ui/ErrorState";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

type Question = {
  key: string;
  number: string;
  prompt: string;
  file: string;
};

type OnboardSession = {
  session_id: string;
  workspace_id: string;
  current_question: number;
  answers: Record<string, string>;
  status: string;
  output_paths: Record<string, string>;
};

export default function AgentOsOnboardPage() {
  const [workspaceId, setWorkspaceId] = React.useState("personal-os");
  const [workspacePath, setWorkspacePath] = React.useState("");
  const [questions, setQuestions] = React.useState<Question[]>([]);
  const [session, setSession] = React.useState<OnboardSession | null>(null);
  const [answer, setAnswer] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const parse = async <T,>(response: Response, fallback: string): Promise<T> => {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(parseApiErrorMessage(payload, fallback));
    }
    return payload as T;
  };

  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      const payload = await parse<{ session: OnboardSession; questions: Question[] }>(
        await ceApi("/api/agent-os/onboard/start", {
          method: "POST",
          body: JSON.stringify({ workspace_id: workspaceId.trim() || "personal-os" }),
        }),
        "Could not start onboard interview",
      );
      setSession(payload.session);
      setQuestions(payload.questions);
      setAnswer(payload.session.answers[`q${payload.session.current_question}`] || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start onboard interview");
    } finally {
      setBusy(false);
    }
  };

  const submitAnswer = async () => {
    if (!session || !answer.trim()) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const payload = await parse<{ session: OnboardSession }>(
        await ceApi(`/api/agent-os/onboard/${encodeURIComponent(session.session_id)}/answer`, {
          method: "POST",
          body: JSON.stringify({ question: session.current_question, text: answer.trim() }),
        }),
        "Could not save answer",
      );
      setSession(payload.session);
      setAnswer(payload.session.answers[`q${payload.session.current_question}`] || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save answer");
    } finally {
      setBusy(false);
    }
  };

  const complete = async () => {
    if (!session) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const payload = await parse<{ session: OnboardSession }>(
        await ceApi(`/api/agent-os/onboard/${encodeURIComponent(session.session_id)}/complete`, {
          method: "POST",
          body: JSON.stringify({ workspace_path: workspacePath.trim() || undefined }),
        }),
        "Could not complete onboard interview",
      );
      setSession(payload.session);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not complete onboard interview");
    } finally {
      setBusy(false);
    }
  };

  const current = questions.find((item) => Number(item.number) === session?.current_question);
  const progress = session ? Math.min(100, ((session.current_question - 1) / 7) * 100) : 0;

  return (
    <Box>
      <PageHeader
        title="Onboard interview"
        description="Seven questions that write workspace context files. Distinct from the activation checklist."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Agent OS", href: AGENT_OS_HUB_HOME },
          { label: "Onboard interview" },
        ]}
        actions={
          <Button component="a" href="/agent-os/onboarding" variant="outlined" size="small">
            Activation checklist
          </Button>
        }
      />

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Stack spacing={2}>
            <TextField label="Workspace id" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)} />
            <TextField
              label="Optional workspace path"
              value={workspacePath}
              onChange={(event) => setWorkspacePath(event.target.value)}
              placeholder="/path/to/workspace"
              helperText="Leave blank to write under KEPRIX_HOME/workspaces/{workspace id}."
            />
            <Button variant="contained" disabled={busy} onClick={() => void start()}>
              {session ? "Resume interview" : "Start interview"}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {error ? (
        <Box sx={{ mb: 2 }}>
          <ErrorState title="Interview error" message={error} />
        </Box>
      ) : null}

      {session ? (
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={2}>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Typography variant="subtitle1">
                  {session.status === "completed" ? "Complete" : `Question ${session.current_question} of 7`}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {session.session_id}
                </Typography>
              </Stack>
              <LinearProgress variant="determinate" value={session.status === "completed" ? 100 : progress} />
              {session.status === "completed" ? (
                <Alert severity="success">
                  Context files written. Next: wire day-2 connections, then run the Four C's maturity audit on day 7.
                </Alert>
              ) : current ? (
                <>
                  <Typography variant="body1">{current.prompt}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Writes {current.file}
                  </Typography>
                  <TextField value={answer} onChange={(event) => setAnswer(event.target.value)} multiline minRows={5} fullWidth />
                  <Button variant="contained" disabled={!answer.trim() || busy} onClick={() => void submitAnswer()}>
                    Save answer
                  </Button>
                </>
              ) : (
                <Button variant="contained" disabled={busy} onClick={() => void complete()}>
                  Complete and write context files
                </Button>
              )}
            </Stack>
          </CardContent>
        </Card>
      ) : null}
    </Box>
  );
}
