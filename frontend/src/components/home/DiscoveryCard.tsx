"use client";

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { IconX } from "@tabler/icons-react";

const DISMISS_TTL_MS = 30 * 24 * 60 * 60 * 1000;

function isDismissed(key: string): boolean {
  try {
    const raw = localStorage.getItem(`discovery_dismiss_${key}`);
    if (!raw) return false;
    return Date.now() - Number(raw) < DISMISS_TTL_MS;
  } catch {
    return false;
  }
}

function dismiss(key: string): void {
  try {
    localStorage.setItem(`discovery_dismiss_${key}`, String(Date.now()));
  } catch {
    /* ignore */
  }
}

type Trigger = {
  key: string;
  title: string;
  body: string;
  actionLabel: string;
  actionHref: string;
};

function selectTrigger(
  conversationCount: number,
  memoryCount: number,
  toolCount: number,
): Trigger | null {
  const candidates: Array<{ check: boolean; trigger: Trigger }> = [
    {
      check: conversationCount >= 10 && memoryCount === 0,
      trigger: {
        key: "brain_discovery",
        title: "Your agent can remember things",
        body: "Your agent has remembered enough context to show it as a graph.",
        actionLabel: "Open brain graph",
        actionHref: "/brain/graph",
      },
    },
    {
      check: conversationCount >= 5 && toolCount === 0,
      trigger: {
        key: "skills_empty",
        title: "Your agent can learn new skills",
        body: "You have had enough sessions to synthesise your first custom tool. Go to Skills to review what is ready.",
        actionLabel: "View Skills",
        actionHref: "/skills",
      },
    },
  ];

  for (const { check, trigger } of candidates) {
    if (check && !isDismissed(trigger.key)) return trigger;
  }
  return null;
}

type Props = {
  conversationCount: number;
  memoryCount: number;
  toolCount: number;
};

export default function DiscoveryCard({ conversationCount, memoryCount, toolCount }: Props) {
  const [trigger, setTrigger] = useState<Trigger | null>(null);

  useEffect(() => {
    setTrigger(selectTrigger(conversationCount, memoryCount, toolCount));
  }, [conversationCount, memoryCount, toolCount]);

  if (!trigger) return null;

  return (
    <Box sx={{ mt: 3 }}>
      <Card
        variant="outlined"
        sx={{
          borderLeft: "3px solid",
          borderLeftColor: "primary.main",
        }}
      >
        <CardContent sx={{ position: "relative", pr: 6 }}>
          <IconButton
            size="small"
            onClick={() => {
              dismiss(trigger.key);
              setTrigger(null);
            }}
            sx={{ position: "absolute", top: 8, right: 8 }}
            aria-label="Dismiss"
          >
            <IconX size={16} stroke={2} />
          </IconButton>
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>
            {trigger.title}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {trigger.body}
          </Typography>
          <Button
            component="a"
            href={trigger.actionHref}
            variant="outlined"
            size="small"
          >
            {trigger.actionLabel}
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
}
