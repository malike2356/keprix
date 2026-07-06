"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { useRouter } from "next/navigation";
import AgentAppCard from "@/components/agent-apps/AgentAppCard";
import AgentAppEmptyState from "@/components/agent-apps/AgentAppEmptyState";
import AgentAppUpgradeBanner from "@/components/agent-apps/AgentAppUpgradeBanner";
import {
  AgentAppApiError,
  fetchAgentApps,
  fetchCatalogTemplates,
  installCatalogTemplate,
} from "@/lib/agent-apps-api";

const CATEGORIES = ["", "productivity", "research", "finance"] as const;

const INTRO_STORAGE_KEY = "keprix.agent_apps.intro.dismissed";

export default function AgentAppHub() {
  const router = useRouter();
  const [tab, setTab] = React.useState(0);
  const [category, setCategory] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [installingId, setInstallingId] = React.useState<string | null>(null);
  const [installError, setInstallError] = React.useState<string | null>(null);
  const [upgradeRequired, setUpgradeRequired] = React.useState(false);
  const [showIntro, setShowIntro] = React.useState(false);

  React.useEffect(() => {
    try {
      setShowIntro(localStorage.getItem(INTRO_STORAGE_KEY) !== "1");
    } catch {
      setShowIntro(true);
    }
  }, []);

  const { data: installed, mutate: mutateInstalled } = useSWR("agent-apps", fetchAgentApps);
  const { data: catalog, mutate: mutateCatalog } = useSWR(
    ["agent-apps-catalog", category, query],
    () => fetchCatalogTemplates(category || undefined, query || undefined),
  );

  const featured = (catalog?.templates ?? []).filter((item) => item.featured).slice(0, 3);
  const installedCount = installed?.apps?.length ?? 0;
  const showFeatured = installedCount <= 2 && featured.length > 0;

  const onInstall = async (templateId: string) => {
    setInstallingId(templateId);
    setInstallError(null);
    setUpgradeRequired(false);
    try {
      const result = await installCatalogTemplate(templateId);
      await mutateInstalled();
      await mutateCatalog();
      router.push(result.redirect || `/agent-apps/${result.app.name}`);
    } catch (err) {
      if (err instanceof AgentAppApiError && (err.status === 402 || err.code === "agent_apps.pro_templates")) {
        setUpgradeRequired(true);
        setInstallError("Pro templates require a paid plan. Upgrade to install this app.");
      } else {
        setInstallError(err instanceof Error ? err.message : "Install failed");
      }
    } finally {
      setInstallingId(null);
    }
  };

  const featuredRow = showFeatured ? (
    <Box>
      <Typography variant="subtitle1" gutterBottom>
        Recommended for you
      </Typography>
      <Box
        sx={{
          display: "flex",
          gap: 2,
          overflowX: "auto",
          pb: 1,
          scrollSnapType: "x mandatory",
        }}
      >
        {featured.map((template) => (
          <Box key={template.id} sx={{ minWidth: { xs: 280, md: 320 }, flex: "0 0 auto", scrollSnapAlign: "start" }}>
            <AgentAppCard
              template={template}
              installing={installingId === template.id}
              onInstall={
                template.installed
                  ? () => router.push(`/agent-apps/${template.name}`)
                  : () => onInstall(template.id)
              }
            />
          </Box>
        ))}
      </Box>
    </Box>
  ) : null;

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      {showIntro ? (
        <Alert
          severity="info"
          onClose={() => {
            setShowIntro(false);
            try {
              localStorage.setItem(INTRO_STORAGE_KEY, "1");
            } catch {
              /* ignore */
            }
          }}
        >
          Install a template from Discover, run it with dynamic forms, then schedule or call it from the API.
        </Alert>
      ) : null}
      <AgentAppUpgradeBanner />
      {featuredRow}

      <Tabs value={tab} onChange={(_, value) => setTab(value)}>
        <Tab label="Installed" />
        <Tab label="Discover" />
      </Tabs>

      {tab === 0 ? (
        <Box sx={{ display: "grid", gap: 2 }}>
          {(installed?.apps ?? []).length === 0 ? (
            <AgentAppEmptyState onBrowseTemplates={() => setTab(1)} />
          ) : (
            <Box
              sx={{
                display: "grid",
                gap: 2,
                gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "1fr 1fr 1fr" },
              }}
            >
              {(installed?.apps ?? []).map((app) => (
                <AgentAppCard key={app.name} app={app} onOpen={() => router.push(`/agent-apps/${app.name}`)} />
              ))}
            </Box>
          )}
        </Box>
      ) : (
        <Box sx={{ display: "grid", gap: 2 }}>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {CATEGORIES.map((value) => (
              <Chip
                key={value || "all"}
                label={value ? value.charAt(0).toUpperCase() + value.slice(1) : "All"}
                color={category === value ? "primary" : "default"}
                onClick={() => setCategory(value)}
                variant={category === value ? "filled" : "outlined"}
              />
            ))}
          </Stack>

          <TextField
            size="small"
            label="Search templates"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            sx={{ maxWidth: 420 }}
          />

          {installError ? (
            <Alert
              severity={upgradeRequired ? "info" : "error"}
              action={
                upgradeRequired ? (
                  <Button color="inherit" size="small" href="/pricing">
                    View plans
                  </Button>
                ) : undefined
              }
            >
              {installError}
            </Alert>
          ) : null}

          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "1fr 1fr 1fr" },
            }}
          >
            {(catalog?.templates ?? []).map((template) => (
              <AgentAppCard
                key={template.id}
                template={template}
                installing={installingId === template.id}
                onInstall={
                  template.installed
                    ? () => router.push(`/agent-apps/${template.name}`)
                    : () => onInstall(template.id)
                }
              />
            ))}
          </Box>
        </Box>
      )}
    </Box>
  );
}
