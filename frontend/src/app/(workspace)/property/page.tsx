"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { fetchPropertySurface, postPropertySurface } from "@/lib/property-api";

const WORKSPACE = "default";
const TABS = [
  ["overview", "Overview"],
  ["discovery", "Discovery"],
  ["saved-searches", "Saved Searches"],
  ["due-diligence", "Due Diligence"],
  ["calculators", "Calculators"],
  ["floor-plan", "Floor Plan"],
  ["workspace", "Property Workspace"],
  ["data-api", "Data API"],
  ["data-layer", "Data Layer"],
] as const;

const EMPTY_SURFACE: Record<string, string> = {
  overview: "Your property pipeline will appear here when a source or saved search is connected.",
  discovery: "Configure signals and run a discovery search to find ranked opportunities.",
  "saved-searches": "Create a saved search to keep matching properties in one workspace.",
  "due-diligence": "Enter a UPRN or address to generate a due diligence report.",
  calculators: "Choose a strategy and enter assumptions to compare returns.",
  "floor-plan": "Upload a floor plan to inspect room data and compliance signals.",
  workspace: "Bridge state and approval proposals will appear here.",
  "data-api": "Create scoped keys for approved integrations and revoke them here.",
  "data-layer": "Connected source health and refresh status will appear here.",
};

function Surface({ name, workspaceId }: { name: string; workspaceId: string }) {
  const surface = useSWR(["property-surface", name, workspaceId], () => fetchPropertySurface(name, workspaceId));
  const [input, setInput] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const busy = surface.isLoading && !surface.data;
  const values = surface.data?.data || {};
  const items = Array.isArray(values.items) ? values.items : [];

  async function runAction() {
    if (!input.trim()) return;
    setMessage(null);
    try {
      await postPropertySurface(name, { query: input.trim() }, workspaceId);
      setInput("");
      setMessage("Request submitted");
      await surface.mutate();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Request failed");
    }
  }

  return (
    <Stack spacing={2}>
      {surface.error ? <Alert severity="error">{surface.error.message}</Alert> : null}
      {!surface.error && surface.data && !surface.data.available ? (
        <Alert severity="info">This property backend is not enabled yet. The workspace is ready and will show live data when it is connected.</Alert>
      ) : null}
      {busy ? <CircularProgress size={26} /> : null}
      <Card variant="outlined">
        <CardContent>
          <Typography variant="body1">{EMPTY_SURFACE[name] || "No records yet."}</Typography>
          {items.length ? (
            <Stack divider={<Divider />} sx={{ mt: 2 }}>
              {items.slice(0, 20).map((item, index) => (
                <Box key={index} sx={{ py: 1 }}>
                  <Typography variant="body2">{typeof item === "object" ? JSON.stringify(item) : String(item)}</Typography>
                </Box>
              ))}
            </Stack>
          ) : null}
        </CardContent>
      </Card>
      {name !== "overview" && name !== "workspace" && name !== "data-layer" ? (
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <TextField
            fullWidth
            size="small"
            label={name === "due-diligence" ? "UPRN or address" : "Search or action input"}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void runAction();
            }}
          />
          <Button variant="contained" onClick={() => void runAction()} disabled={!input.trim()}>
            {name === "discovery" ? "Run discovery" : "Submit"}
          </Button>
        </Stack>
      ) : null}
      {message ? <Alert severity={message === "Request submitted" ? "success" : "warning"}>{message}</Alert> : null}
    </Stack>
  );
}

export default function PropertyPage() {
  const [tab, setTab] = React.useState(0);
  const [prompt, setPrompt] = React.useState("");
  const active = TABS[tab];
  const askHref = prompt.trim() ? `/chat?prompt=${encodeURIComponent(prompt.trim())}` : "/chat";

  return (
    <Stack spacing={2.5} sx={{ maxWidth: 1440, mx: "auto", width: "100%" }}>
      <Box>
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ sm: "center" }} spacing={1}>
          <Box>
            <Typography variant="h5">Property Command Center</Typography>
            <Typography variant="body2" color="text.secondary">Workspace-scoped property research, analysis, and approved handoffs.</Typography>
          </Box>
          <Chip label={`Workspace: ${WORKSPACE}`} size="small" variant="outlined" />
        </Stack>
      </Box>
      <Card variant="outlined">
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1} alignItems={{ md: "center" }}>
            <TextField
              fullWidth
              size="small"
              label="Ask about a property"
              placeholder="Find undervalued flats in Portsmouth"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
            />
            <Button component="a" href={askHref} variant="contained" disabled={!prompt.trim()}>Ask</Button>
          </Stack>
        </CardContent>
      </Card>
      <Tabs value={tab} onChange={(_, value: number) => setTab(value)} variant="scrollable" allowScrollButtonsMobile>
        {TABS.map(([, label]) => <Tab key={label} label={label} />)}
      </Tabs>
      <Box aria-live="polite"><Surface name={active[0]} workspaceId={WORKSPACE} /></Box>
    </Stack>
  );
}
