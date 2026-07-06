"use client";

import type { ReactNode } from "react";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Avatar from "@mui/material/Avatar";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { AgentAppSummary, CatalogTemplate } from "@/lib/agent-apps-api";

type Props = {
  app?: AgentAppSummary;
  template?: CatalogTemplate;
  onOpen?: () => void;
  onInstall?: () => void;
  installing?: boolean;
};

function tierLabel(tier?: string) {
  if (!tier) return null;
  return tier === "free" ? "Free" : tier.charAt(0).toUpperCase() + tier.slice(1);
}

function categoryLabel(value?: string) {
  if (!value) return "Custom";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function iconLetter(title: string) {
  const trimmed = title.trim();
  return trimmed ? trimmed.charAt(0).toUpperCase() : "A";
}

export default function AgentAppCard({ app, template, onOpen, onInstall, installing }: Props) {
  const title = app?.display_name || template?.display_name || app?.name || template?.name || "Agent app";
  const description = app?.description || template?.description || "";
  const version = app?.version;
  const tier = template?.tier;
  const proLocked = template?.pro_locked;
  const installed = template?.installed;
  const action = proLocked ? undefined : onInstall ? onInstall : onOpen;
  const cta = installing
    ? "Installing..."
    : proLocked
      ? "Pro plan required"
      : onInstall && !installed
        ? "Install"
        : onOpen
          ? "Open"
          : onInstall && installed
            ? "Open"
            : "";

  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardActionArea onClick={action} disabled={installing || proLocked || !action} sx={{ height: "100%", alignItems: "stretch" }}>
        <CardContent sx={{ display: "grid", gap: 1.5, height: "100%" }}>
          <Stack direction="row" spacing={1.5} alignItems="flex-start">
            <Avatar
              sx={{
                width: 40,
                height: 40,
                bgcolor: "primary.main",
                fontSize: "1rem",
                fontWeight: 600,
              }}
            >
              {iconLetter(title)}
            </Avatar>
            <BoxGrow>
              <Stack direction="row" spacing={0.5} alignItems="center" flexWrap="wrap" useFlexGap>
                <Typography variant="subtitle1" fontWeight={600}>
                  {title}
                </Typography>
                {version ? <Chip size="small" label={`v${version}`} /> : null}
                {tier ? (
                  <Chip
                    size="small"
                    color={tier === "free" ? "default" : "primary"}
                    label={tierLabel(tier)}
                    variant={proLocked ? "outlined" : "filled"}
                  />
                ) : null}
                {proLocked ? <Chip size="small" color="warning" label="Upgrade" /> : null}
                {installed ? <Chip size="small" color="success" label="Installed" /> : null}
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {description}
              </Typography>
            </BoxGrow>
          </Stack>
          <Typography variant="caption" color="text.secondary">
            {categoryLabel(app?.category || template?.category)}
            {cta ? ` · ${cta}` : ""}
          </Typography>
        </CardContent>
      </CardActionArea>
    </Card>
  );
}

function BoxGrow({ children }: { children: ReactNode }) {
  return <div style={{ flex: 1, minWidth: 0 }}>{children}</div>;
}
