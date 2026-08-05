"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import * as React from "react";
import NextLink from "next/link";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import PersonalOsStarterCard from "@/components/hub/PersonalOsStarterCard";
import { fetchHubCatalog, installHubPack, type HubPack } from "@/lib/hub-api";

function PackGrid({
  items,
  onInstall,
}: {
  items: HubPack[];
  onInstall: (pack: HubPack) => Promise<void>;
}) {
  return (
    <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { md: "1fr 1fr" } }}>
      {items.map((pack) => (
        <Card key={`${pack.name}-${pack.version}`} variant="outlined">
          <CardContent>
            <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1, mb: 1 }}>
              <Typography variant="h6">{pack.name}</Typography>
              <Chip size="small" label={pack.risk_level} />
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {pack.description || pack.type}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              v{pack.version} by {pack.author}
            </Typography>
            <Button
              sx={{ mt: 2 }}
              variant={pack.installed ? "outlined" : "contained"}
              disabled={pack.installed}
              onClick={() => void onInstall(pack)}
            >
              {pack.installed ? "Installed" : "Install"}
            </Button>
          </CardContent>
        </Card>
      ))}
    </Box>
  );
}

export default function HubPage() {
  const { data, mutate } = useSWR("hub-catalog", fetchHubCatalog);
  const [tab, setTab] = React.useState(0);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const handleInstall = async (pack: HubPack) => {
    setError(null);
    setMessage(null);
    try {
      const result = await installHubPack(pack.name, pack.risk_level !== "low");
      if (result.status === "awaiting_approval") {
        const approved = await installHubPack(pack.name, true);
        setMessage(`Installed ${pack.name} (${approved.status})`);
      } else {
        setMessage(`Installed ${pack.name}`);
      }
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Install failed");
    }
  };

  const packs = data?.packs ?? [];
  const templates = data?.templates ?? [];
  const connectors = data?.connectors ?? [];

  return (
    <Box>
      <PageHeader
        title="Hub"
        description="Install skill packs, app templates, and connectors with manifest checks and rollback."
        actions={
          <Button component={NextLink} href="/integrations" variant="outlined">
            Browse all integrations
          </Button>
        }
      />
      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent sx={{ display: "flex", flexWrap: "wrap", gap: 2, alignItems: "center", justifyContent: "space-between" }}>
          <Box>
            <Typography variant="h6">Agent Apps</Typography>
            <Typography variant="body2" color="text.secondary">
              Install ready-made workflows or ship your own apps.
            </Typography>
          </Box>
          <Button component={NextLink} href="/agent-apps" variant="contained">
            Open Agent Apps
          </Button>
        </CardContent>
      </Card>
      <PersonalOsStarterCard
        pack={packs.find((pack) => pack.name === "keprix-personal-os-starter")}
        onInstall={(packName) => {
          const pack = packs.find((item) => item.name === packName);
          if (pack) void handleInstall(pack);
        }}
      />
      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 2 }}>
        <Tab label={`Packs (${packs.length})`} />
        <Tab label={`Templates (${templates.length})`} />
        <Tab label={`Connectors (${connectors.length})`} />
      </Tabs>
      {tab === 0 ? <PackGrid items={packs} onInstall={handleInstall} /> : null}
      {tab === 1 ? <PackGrid items={templates} onInstall={handleInstall} /> : null}
      {tab === 2 ? <PackGrid items={connectors} onInstall={handleInstall} /> : null}
    </Box>
  );
}
