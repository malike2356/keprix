"use client";

import CloseIcon from "@mui/icons-material/Close";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { ceApi } from "@/lib/ce-api";

type NextActivation = {
  id: string;
  title: string;
  action_url: string;
  copy?: string;
};

type OnboardingPayload = {
  banner_visible: boolean;
  completed_count: number;
  total_count: number;
  activation_completed?: boolean;
  next_activation?: NextActivation | null;
};

async function fetchOnboarding(): Promise<OnboardingPayload> {
  const response = await ceApi("/api/agent-os/onboarding");
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as OnboardingPayload;
}

export default function OnboardingBanner() {
  const { data, mutate } = useSWR("agent-os-onboarding-banner", fetchOnboarding, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });
  const [locallyHidden, setLocallyHidden] = React.useState(false);

  if (!data?.banner_visible || locallyHidden) return null;

  const next = data.next_activation;
  const progress = data.total_count > 0 ? Math.round((data.completed_count / data.total_count) * 100) : 0;

  const dismiss = async () => {
    setLocallyHidden(true);
    try {
      const response = await ceApi("/api/agent-os/onboarding/dismiss", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dismissed: true }),
      });
      if (response.ok) {
        await mutate();
        return;
      }
      setLocallyHidden(false);
    } catch {
      setLocallyHidden(false);
    }
  };

  return (
    <Paper
      variant="outlined"
      sx={{
        mb: 2,
        p: 2,
        display: "grid",
        gap: 1.5,
        borderColor: "primary.main",
        bgcolor: "background.paper",
      }}
    >
      <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle1">
            {next ? `Next: ${next.title}` : "Finish workspace activation"}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {next?.copy || `${data.completed_count} of ${data.total_count} steps complete.`}
          </Typography>
        </Box>
        <Button
          href={next?.action_url || "/agent-os/onboarding"}
          variant="contained"
          size="small"
          sx={{
            color: "primary.contrastText",
            bgcolor: "primary.main",
            "&:hover": { bgcolor: "primary.dark", color: "primary.contrastText" },
          }}
        >
          {next ? "Continue" : "Open activation"}
        </Button>
        <Button size="small" color="inherit" onClick={() => void dismiss()}>
          Skip for now
        </Button>
        <IconButton size="small" aria-label="Dismiss onboarding" onClick={() => void dismiss()}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>
      <LinearProgress variant="determinate" value={progress} sx={{ height: 6, borderRadius: 1 }} />
    </Paper>
  );
}
