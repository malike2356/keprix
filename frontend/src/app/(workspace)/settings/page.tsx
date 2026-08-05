"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActions from "@mui/material/CardActions";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Grid from "@mui/material/Grid2";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Paper from "@mui/material/Paper";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import BackupIcon from "@mui/icons-material/Backup";
import CodeIcon from "@mui/icons-material/Code";
import CreditCardIcon from "@mui/icons-material/CreditCard";
import ExtensionIcon from "@mui/icons-material/Extension";
import GridViewIcon from "@mui/icons-material/GridView";
import GroupIcon from "@mui/icons-material/Group";
import KeyIcon from "@mui/icons-material/Key";
import LockIcon from "@mui/icons-material/Lock";
import ScheduleIcon from "@mui/icons-material/Schedule";
import SettingsIcon from "@mui/icons-material/Settings";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import TranslateIcon from "@mui/icons-material/Translate";
import ViewListIcon from "@mui/icons-material/ViewList";
import MicIcon from "@mui/icons-material/Mic";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import ThemeAppearancePanel from "@/components/theme/ThemeAppearancePanel";
import { useCESession } from "@/lib/ce-auth";
import { fetchDeveloperIdentity } from "@/lib/admin-workspace-api";

type SettingsViewMode = "list" | "cards";

const SETTINGS_VIEW_MODE_KEY = "keprix_settings_view_mode";

type SettingsCard = {
  title: string;
  description: string;
  href: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
};

const cards: SettingsCard[] = [
  {
    title: "Vault",
    description: "Store passwords, API keys, and tokens encrypted at rest.",
    href: "/vault",
    icon: <LockIcon />,
  },
  {
    title: "Cron jobs",
    description: "Schedule recurring agent tasks and review run history.",
    href: "/admin/cron",
    icon: <ScheduleIcon />,
  },
  {
    title: "MCP servers",
    description:
      "Connect MCP servers, or use skills and RAG for Notion and Trello without MCP.",
    href: "/admin/mcp",
    icon: <ExtensionIcon />,
  },
  {
    title: "GitHub agent-sync",
    description: "Shared durable memory with Fowler (Hermes), Carina, and Aiva. Configure token and sync from the GUI.",
    href: "/settings/integrations/agent-sync",
    icon: <BackupIcon />,
  },
  {
    title: "Syncthing (Obsidian vault)",
    description: "Vault-only folder sync with a one-writer rule. Keep memory/skills on agent-sync, not here.",
    href: "/settings/integrations/syncthing",
    icon: <BackupIcon />,
  },
  {
    title: "Backup",
    description: "Export and restore workspace data and configuration.",
    href: "/admin/backup",
    icon: <BackupIcon />,
  },
  {
    title: "Developer platform",
    description: "API keys, webhooks, and OpenAI-compatible endpoints.",
    href: "/developer",
    icon: <CodeIcon />,
  },
  {
    title: "Privacy",
    description: "Consent records, DSAR exports, and data erasure.",
    href: "/privacy",
    icon: <LockIcon />,
  },
  {
    title: "Voice templates",
    description: "Pre-recorded phrases for Ghanaian languages; hybrid TTS for dynamic content.",
    href: "/settings/voice-templates",
    icon: <SettingsIcon />,
  },
  {
    title: "Voice input (STT)",
    description: "Enable speech-to-text, choose provider, set max recording, and manage API keys from the GUI.",
    href: "/settings/voice",
    icon: <MicIcon />,
  },
  {
    title: "Localization corrections",
    description: "Review user corrections, apply glossary updates, and stage training samples.",
    href: "/settings/localization/corrections",
    icon: <TranslateIcon />,
    adminOnly: true,
  },
  {
    title: "Localization metrics",
    description: "Correction rates, provider accuracy, and fine-tuning export readiness.",
    href: "/settings/localization/metrics",
    icon: <TranslateIcon />,
    adminOnly: true,
  },
  {
    title: "Browser harness",
    description: "Agent browser sessions, encrypted profiles, and skill benchmarks.",
    href: "/settings/browser",
    icon: <ExtensionIcon />,
  },
  {
    title: "Pack gate",
    description: "Require clinical sign-off before new pack versions activate.",
    href: "/settings/pack-gate",
    icon: <LockIcon />,
    adminOnly: true,
  },
  {
    title: "Notification preferences",
    description: "Inbox channels, quiet hours, digests, and approval escalation timing.",
    href: "/settings/notifications",
    icon: <SettingsIcon />,
  },
  {
    title: "External notifications",
    description: "SMTP delivery to external reviewers and compliance contacts.",
    href: "/settings/notifications/external",
    icon: <SettingsIcon />,
    adminOnly: true,
  },
  {
    title: "Evidence packs",
    description: "Signed audit event archives for auditors and governance providers.",
    href: "/settings/governance/evidence-packs",
    icon: <LockIcon />,
    adminOnly: true,
  },
  {
    title: "Governance",
    description: "Connect a governance provider for kill switches, audit trails, and policy enforcement.",
    href: "/settings/governance",
    icon: <SettingsIcon />,
  },
  {
    title: "Workspace users",
    description: "Invite people, assign roles (owner, admin, user), and manage human access.",
    href: "/settings/users",
    icon: <GroupIcon />,
    adminOnly: true,
  },
  {
    title: "Agent teams",
    description: "CrewAI-style YAML agent crews (roles and tasks). Agent workflows, not human accounts.",
    href: "/admin/teams",
    icon: <SmartToyIcon />,
  },
  {
    title: "Billing and subscription",
    description: "Manage your SaaS plan, payment method, invoices, and team seats.",
    href: "/settings/billing",
    icon: <CreditCardIcon />,
  },
  {
    title: "LLM usage",
    description: "Token consumption, estimated spend, budgets, and CSV/JSON export.",
    href: "/data?tab=usage",
    icon: <SettingsIcon />,
  },
  {
    title: "Web search",
    description: "Configure Tavily, SearXNG, or other providers for deep research.",
    href: "/settings/web-search",
    icon: <SettingsIcon />,
    adminOnly: true,
  },
  {
    title: "Companies House",
    description: "UK company search and profiles via the Companies House Public Data API.",
    href: "/settings/companies-house",
    icon: <SettingsIcon />,
  },
  {
    title: "Instance settings",
    description: "LLM providers, agent behaviour, storage, and channels.",
    href: "/dashboard/settings",
    icon: <SettingsIcon />,
    adminOnly: true,
  },
];

function readSettingsViewMode(): SettingsViewMode {
  if (typeof window === "undefined") return "list";
  const stored = localStorage.getItem(SETTINGS_VIEW_MODE_KEY);
  return stored === "cards" ? "cards" : "list";
}

function storeSettingsViewMode(mode: SettingsViewMode): void {
  localStorage.setItem(SETTINGS_VIEW_MODE_KEY, mode);
}

export default function SettingsPage() {
  const { user } = useCESession();
  const isAdmin = user?.role === "admin" || user?.role === "owner";
  const { data: identity } = useSWR(isAdmin ? "settings-identity" : null, fetchDeveloperIdentity);
  const visibleCards = cards.filter((card) => !card.adminOnly || isAdmin);
  const [viewMode, setViewMode] = React.useState<SettingsViewMode>("list");

  React.useEffect(() => {
    setViewMode(readSettingsViewMode());
  }, []);

  const handleViewModeChange = (_event: React.MouseEvent<HTMLElement>, next: SettingsViewMode | null) => {
    if (!next) return;
    setViewMode(next);
    storeSettingsViewMode(next);
  };

  return (
    <Box>
      <PageHeader title="Settings" description="Configure providers, channels, identity, and workspace tools." />
      {identity ? (
        <Card variant="outlined" sx={{ mb: 2 }}>
          <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
            <Typography variant="subtitle1">Developer identity</Typography>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5, flexWrap: "wrap" }}>
              <Typography variant="body2" color="text.secondary" component="span">
                Fingerprint:
              </Typography>
              <Chip size="small" label={identity.fingerprint} />
            </Box>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
              Config: {identity.config_path}
            </Typography>
          </CardContent>
          <CardActions sx={{ pt: 0 }}>
            <Button component={NextLink} href="/developer" size="small" startIcon={<KeyIcon />}>
              Manage API keys
            </Button>
          </CardActions>
        </Card>
      ) : null}
      <ThemeAppearancePanel />
      <Box
        sx={{
          mt: 2,
          mb: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 1,
          flexWrap: "wrap",
        }}
      >
        <Typography variant="subtitle1">Workspace settings</Typography>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={viewMode}
          onChange={handleViewModeChange}
          aria-label="Settings layout"
        >
          <ToggleButton value="list" aria-label="List view">
            <ViewListIcon fontSize="small" sx={{ mr: 0.75 }} />
            List
          </ToggleButton>
          <ToggleButton value="cards" aria-label="Card view">
            <GridViewIcon fontSize="small" sx={{ mr: 0.75 }} />
            Cards
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {viewMode === "list" ? (
        <Paper variant="outlined">
          <List disablePadding>
            {visibleCards.map((card, index) => (
              <React.Fragment key={card.href}>
                {index > 0 ? <Divider component="li" /> : null}
                <ListItemButton component={NextLink} href={card.href} sx={{ py: 1.25 }}>
                  <ListItemIcon sx={{ minWidth: 40 }}>{card.icon}</ListItemIcon>
                  <ListItemText
                    primary={card.title}
                    secondary={card.description}
                    primaryTypographyProps={{ variant: "body1", fontWeight: 500 }}
                    secondaryTypographyProps={{
                      variant: "body2",
                      color: "text.secondary",
                      sx: {
                        display: "-webkit-box",
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                      },
                    }}
                  />
                  <ChevronRightIcon fontSize="small" color="action" />
                </ListItemButton>
              </React.Fragment>
            ))}
          </List>
        </Paper>
      ) : (
        <Grid container spacing={2}>
          {visibleCards.map((card) => (
            <Grid key={card.href} size={{ xs: 12, sm: 6, md: 4 }}>
              <Card variant="outlined" sx={{ height: "100%" }}>
                <CardContent>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                    {card.icon}
                    <Typography variant="h6">{card.title}</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {card.description}
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button component={NextLink} href={card.href} size="small">
                    Open
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
}
