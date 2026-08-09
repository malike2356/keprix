"use client";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { AGENT_OS_HUB_HOME } from "@/components/agent-os/AgentOsSubnav";
import MilestonesPanel from "@/components/agent-os/MilestonesPanel";
import ErrorState from "@/components/ui/ErrorState";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

type StepDefinition = {
  id: string;
  level: number;
  title: string;
  action_url: string;
  auto_complete: string;
  copy?: string;
  track?: "activation" | "maturity";
};

type OnboardingPayload = {
  steps: Record<string, boolean>;
  step_definitions: StepDefinition[];
  completed_at: string | null;
  completed_count: number;
  total_count: number;
  activation_completed?: boolean;
  next_activation?: StepDefinition | null;
};

const levelLabels: Record<number, string> = {
  0: "Onboard",
  1: "Skills and loops",
  2: "Memory map",
  3: "Action surface",
  4: "Distribution",
};

async function fetchOnboarding(): Promise<OnboardingPayload> {
  const response = await ceApi("/api/agent-os/onboarding");
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as OnboardingPayload;
}

export default function AgentOsOnboardingPage() {
  const { data, error, mutate } = useSWR("agent-os-onboarding", fetchOnboarding);
  const [whyOpen, setWhyOpen] = React.useState(true);
  const [message, setMessage] = React.useState<string | null>(null);

  const markDone = async (stepId: string) => {
    const response = await ceApi("/api/agent-os/onboarding/complete-step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ step_id: stepId }),
    });
    if (!response.ok) {
      setMessage(await response.text());
      return;
    }
    setMessage(null);
    await mutate();
  };

  const reset = async () => {
    const response = await ceApi("/api/agent-os/onboarding/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      setMessage(await response.text());
      return;
    }
    await mutate();
  };

  const completeAll = async () => {
    const response = await ceApi("/api/agent-os/onboarding/complete-all", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) {
      setMessage(await response.text());
      return;
    }
    setMessage(null);
    await mutate();
  };

  const dismiss = async () => {
    const response = await ceApi("/api/agent-os/onboarding/dismiss", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dismissed: true }),
    });
    if (!response.ok) {
      setMessage(await response.text());
      return;
    }
    setMessage(null);
    await mutate();
  };

  const steps = data?.step_definitions ?? [];
  const activationSteps = steps.filter((step) => (step.track || "maturity") === "activation");
  const maturitySteps = steps.filter((step) => (step.track || "maturity") === "maturity");
  const grouped = [0, 1, 2, 3, 4].map((level) => ({
    level,
    steps: maturitySteps.filter((step) => step.level === level),
  }));
  const overall = data && data.total_count > 0 ? Math.round((data.completed_count / data.total_count) * 100) : 0;
  const activationDone = activationSteps.filter((step) => data?.steps[step.id]).length;
  const activationPct =
    activationSteps.length > 0 ? Math.round((activationDone / activationSteps.length) * 100) : 100;

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Activation checklist"
        description="Day 1 / 7 / 30 milestones, then connect a provider and complete activation. Use Onboard interview for the seven-question workspace write."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Agent OS", href: AGENT_OS_HUB_HOME },
          { label: "Onboarding" },
        ]}
        actions={
          <Stack direction="row" spacing={1}>
            <Button component="a" href="/agent-os/onboard" variant="outlined" size="small">
              Onboard interview
            </Button>
            <Button href="/docs/features/agent-os-overview" variant="outlined" size="small">
              Docs
            </Button>
          </Stack>
        }
      />

      <MilestonesPanel />

      {error ? (
        <ErrorState
          title="Onboarding failed to load"
          message={error instanceof Error ? error.message : "Failed to load onboarding"}
        />
      ) : null}
      {message ? <Typography color="error">{message}</Typography> : null}

      <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 1.5 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, alignItems: "center", flexWrap: "wrap" }}>
          <Box>
            <Typography variant="h6">
              {data?.activation_completed ? "Activation complete" : "Activation"}
            </Typography>
            <Typography color="text.secondary" variant="body2">
              {activationDone} of {activationSteps.length} activation steps
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <Button size="small" variant="outlined" onClick={() => void dismiss()}>
              Skip for now
            </Button>
            <Button size="small" onClick={() => void reset()}>Reset</Button>
          </Box>
        </Box>
        <LinearProgress variant="determinate" value={activationPct} sx={{ height: 8, borderRadius: 1 }} />
        <Box sx={{ display: "grid", gap: 1 }}>
          {activationSteps.map((step) => {
            const checked = Boolean(data?.steps[step.id]);
            return (
              <Box
                key={step.id}
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "32px 1fr auto" },
                  gap: 1.5,
                  alignItems: "center",
                  py: 1,
                  borderTop: "1px solid",
                  borderColor: "divider",
                }}
              >
                <IconButton size="small" aria-label={checked ? "Completed" : "Pending"} disabled>
                  {checked ? <CheckCircleIcon color="success" fontSize="small" /> : <RadioButtonUncheckedIcon fontSize="small" />}
                </IconButton>
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="body2">{step.title}</Typography>
                  {step.copy ? (
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                      {step.copy}
                    </Typography>
                  ) : null}
                </Box>
                <Button href={step.action_url} size="small" variant={checked ? "outlined" : "contained"}>
                  {checked ? "Open" : "Start"}
                </Button>
              </Box>
            );
          })}
        </Box>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
          <Typography variant="subtitle1">Level up Agent OS (optional)</Typography>
          <Button size="small" onClick={() => setWhyOpen((open) => !open)}>
            {whyOpen ? "Hide" : "Show"}
          </Button>
        </Box>
        <Collapse in={whyOpen}>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2 }}>
            These maturity steps auto-complete from real usage. Use Mark done only when you want to skip detection.
          </Typography>
          <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, alignItems: "center", flexWrap: "wrap", mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              {data ? `${data.completed_count} of ${data.total_count} total` : "Loading"} ({overall}%)
            </Typography>
            <Button size="small" variant="outlined" onClick={() => void completeAll()}>
              Mark all done
            </Button>
          </Box>
        </Collapse>
      </Paper>

      {grouped.filter((group) => group.steps.length > 0).map((group) => {
        const done = group.steps.filter((step) => data?.steps[step.id]).length;
        const progress = group.steps.length > 0 ? Math.round((done / group.steps.length) * 100) : 0;
        return (
          <Paper key={group.level} variant="outlined" sx={{ p: 2, display: "grid", gap: 2 }}>
            <Box sx={{ display: "flex", gap: 2, justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
              <Box>
                <Typography variant="h6">L{group.level} {levelLabels[group.level]}</Typography>
                <Typography variant="body2" color="text.secondary">{done} of {group.steps.length} complete</Typography>
              </Box>
              <Chip size="small" label={`${progress}%`} />
            </Box>
            <LinearProgress variant="determinate" value={progress} sx={{ height: 6, borderRadius: 1 }} />
            <Box sx={{ display: "grid", gap: 1 }}>
              {group.steps.map((step) => {
                const checked = Boolean(data?.steps[step.id]);
                return (
                  <Box
                    key={step.id}
                    sx={{
                      display: "grid",
                      gridTemplateColumns: { xs: "1fr", sm: "32px 1fr auto auto" },
                      gap: 1.5,
                      alignItems: "center",
                      py: 1,
                      borderTop: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <IconButton size="small" aria-label={checked ? "Completed" : "Pending"} disabled>
                      {checked ? <CheckCircleIcon color="success" fontSize="small" /> : <RadioButtonUncheckedIcon fontSize="small" />}
                    </IconButton>
                    <Box sx={{ minWidth: 0 }}>
                      <Typography variant="body2">{step.title}</Typography>
                      <Typography variant="caption" color="text.secondary">{step.auto_complete}</Typography>
                      {step.copy ? <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{step.copy}</Typography> : null}
                    </Box>
                    <Button href={step.action_url} size="small" variant="outlined">
                      Open
                    </Button>
                    <Button size="small" disabled={checked} onClick={() => void markDone(step.id)}>
                      Mark done
                    </Button>
                  </Box>
                );
              })}
            </Box>
          </Paper>
        );
      })}
      {data?.completed_at ? (
        <Stack direction="row" spacing={1} alignItems="center">
          <CheckCircleIcon color="success" fontSize="small" />
          <Typography color="text.secondary">Agent OS onboarding is complete.</Typography>
        </Stack>
      ) : null}
    </Box>
  );
}
