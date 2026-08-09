"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useRouter } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import {
  fetchDiscoveryAdapters,
  fetchCrmIcps,
  runDiscoveryJob,
} from "@/lib/crm-api";

const PRIMARY_ADAPTERS = [
  { id: "companies_house", label: "Companies House" },
  { id: "csv", label: "CSV upload" },
  { id: "web_directory", label: "Web / directory" },
  { id: "property_csv", label: "Property CSV" },
  { id: "health_csv", label: "Health / care CSV" },
  { id: "social_csv_export", label: "Social ads CSV export" },
  { id: "linkedin_api", label: "LinkedIn API" },
  { id: "meta_graph", label: "Meta Graph API" },
  { id: "tiktok_api", label: "TikTok API" },
  { id: "cqc_api", label: "CQC API" },
  { id: "fake", label: "Fake (test)" },
] as const;

export default function CrmDiscoverPage() {
  const router = useRouter();
  const workspaceId = CRM_WORKSPACE;
  const adapters = useSWR(["crm-discovery-adapters", workspaceId], () =>
    fetchDiscoveryAdapters(workspaceId),
  );

  const [adapter, setAdapter] = React.useState("companies_house");
  const [query, setQuery] = React.useState("");
  const [location, setLocation] = React.useState("");
  const [domainPack, setDomainPack] = React.useState("generic");
  const [listName, setListName] = React.useState("");
  const [csvText, setCsvText] = React.useState("");
  const [autoMaterialize, setAutoMaterialize] = React.useState(true);
  const [force, setForce] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [icpId, setIcpId] = React.useState("");

  const icps = useSWR(["crm-icp-discover", workspaceId], () => fetchCrmIcps(workspaceId));

  const healthByName = React.useMemo(() => {
    const map = new Map<string, { status?: string; message?: string; enabled?: boolean }>();
    for (const item of adapters.data?.health ?? []) {
      map.set(String(item.name), item);
    }
    return map;
  }, [adapters.data]);

  const selectedHealth = healthByName.get(adapter);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const params: Record<string, unknown> = {};
      if (location) params.location = location;
      if (csvText.trim()) params.csv_text = csvText;
      const result = await runDiscoveryJob(
        {
          adapter,
          query: query || undefined,
          params,
          domain_pack: domainPack,
          list_name: listName || undefined,
          auto_materialize: autoMaterialize,
          materialize: autoMaterialize,
          force,
          run_now: true,
          limits: { max_results: 50 },
          icp_id: icpId || undefined,
        },
        workspaceId,
      );
      if (result.refused) {
        setError(result.message || "Request refused");
        return;
      }
      const jobId = result.job?.id;
      const listId = result.materialize?.list_id || result.job?.list_id;
      const softWall = result.materialize?.blocked;
      if (softWall) {
        setMessage(
          `Discovery finished with Soft Wall pending before List materialize. Job ${jobId}.`,
        );
      } else {
        setMessage(
          `Discovery job ${jobId}${listId ? ` created list ${listId}` : ""}.`,
        );
      }
      if (jobId) {
        router.push(`/crm/jobs/${encodeURIComponent(String(jobId))}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Discovery run failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
      <Card variant="outlined">
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Find companies
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Run a discovery adapter into a CRM DiscoveryJob. Soft Wall may gate List materialize.
            Discovery candidates are not contactable until a separate policy decision.
          </Typography>

          {adapters.error ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {adapters.error instanceof Error
                ? adapters.error.message
                : "Could not load adapters"}
            </Alert>
          ) : null}
          {error ? (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          ) : null}
          {message ? (
            <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
              {message}
            </Alert>
          ) : null}

          <Stack component="form" spacing={2} onSubmit={onSubmit}>
            <FormControl fullWidth size="small">
              <InputLabel id="adapter-label">Adapter</InputLabel>
              <Select
                labelId="adapter-label"
                label="Adapter"
                value={adapter}
                onChange={(e) => setAdapter(e.target.value)}
              >
                {PRIMARY_ADAPTERS.map((item) => {
                  const health = healthByName.get(item.id);
                  const disabled =
                    health?.status === "disabled" || health?.enabled === false;
                  return (
                    <MenuItem key={item.id} value={item.id} disabled={disabled}>
                      {item.label}
                      {health?.status ? ` (${health.status})` : ""}
                    </MenuItem>
                  );
                })}
              </Select>
            </FormControl>

            {selectedHealth ? (
              <Typography variant="body2" color="text.secondary">
                Adapter health: {selectedHealth.status}
                {selectedHealth.message ? `; ${selectedHealth.message}` : ""}
              </Typography>
            ) : null}

            <TextField
              label="Query / keywords"
              size="small"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. plumbers Manchester"
              helperText="Companies House and web directory use this as the search query."
            />
            <TextField
              label="Location"
              size="small"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Optional location filter"
            />
            <FormControl fullWidth size="small">
              <InputLabel id="pack-label">Domain pack</InputLabel>
              <Select
                labelId="pack-label"
                label="Domain pack"
                value={domainPack}
                onChange={(e) => setDomainPack(e.target.value)}
              >
                <MenuItem value="generic">generic</MenuItem>
                <MenuItem value="property">property</MenuItem>
                <MenuItem value="health_social">health_social</MenuItem>
                <MenuItem value="plumbing">plumbing</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth size="small">
              <InputLabel id="icp-label">ICP version</InputLabel>
              <Select
                labelId="icp-label"
                label="ICP version"
                value={icpId}
                onChange={(e) => setIcpId(e.target.value)}
              >
                <MenuItem value="">Active / none</MenuItem>
                {(icps.data?.items || []).map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.name} v{row.version}
                    {row.active ? " (active)" : ""}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="Draft list name"
              size="small"
              value={listName}
              onChange={(e) => setListName(e.target.value)}
              placeholder="Optional"
            />
            {(adapter === "csv" ||
              adapter === "property_csv" ||
              adapter === "health_csv" ||
              adapter === "social_csv_export") && (
              <TextField
                label="CSV text"
                size="small"
                value={csvText}
                onChange={(e) => setCsvText(e.target.value)}
                multiline
                minRows={4}
                placeholder={"company,email,phone\nAcme Ltd,ops@acme.example,+441111"}
              />
            )}
            <FormControlLabel
              control={
                <Switch
                  checked={autoMaterialize}
                  onChange={(e) => setAutoMaterialize(e.target.checked)}
                />
              }
              label="Soft Wall create List after run"
            />
            <FormControlLabel
              control={<Switch checked={force} onChange={(e) => setForce(e.target.checked)} />}
              label="Force Soft Wall bypass (dev only)"
            />
            <Stack direction="row" spacing={1}>
              <Button type="submit" variant="contained" disabled={busy}>
                {busy ? "Running..." : "Run discovery"}
              </Button>
              <Button component="a" href="/crm/jobs" variant="outlined">
                Job history
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      <Typography variant="body2" color="text.secondary">
        Portal scrapers (Rightmove/Zoopla) stay off by default. Social platforms are API-first;
        scrape requests are refused. See docs under docs/features and docs/security.
      </Typography>
    </Stack>
  );
}
