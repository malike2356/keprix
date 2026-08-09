"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import Grid from "@mui/material/Grid2";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import ControlCenter from "@/components/outreach/ControlCenter";
import MetricCards from "@/components/outreach/MetricCards";
import { PIPELINE_STAGES, pipelineLabel } from "@/components/outreach/types";
import {
  createOutreachCampaign,
  enrollOutreachLead,
  fetchOutreachControl,
  fetchOutreachLeads,
  fetchOutreachOverview,
  fetchOutreachSchedulerHealth,
  fetchOutreachSequences,
  importCompaniesHouseLead,
  importOutreachLeads,
  patchOutreachControl,
  processOutreachDue,
} from "@/lib/outreach-api";
import {
  fetchCompanyProfile,
  searchCompaniesHouse,
  type CompanyProfile,
  type CompanySearchHit,
} from "@/lib/companies-house-api";

const WORKSPACE = "default";

const QUICK_LINKS = [
  { href: "/outreach/leads", label: "Leads", description: "Import, edit, and route leads." },
  { href: "/outreach/pipeline", label: "Pipeline", description: "See the live board by status." },
  { href: "/outreach/replies", label: "Replies", description: "Review inbound replies." },
  { href: "/outreach/bookings", label: "Bookings", description: "Schedule and confirm meetings." },
  { href: "/outreach/lists", label: "Lists", description: "Organize audiences and membership." },
  { href: "/outreach/campaigns", label: "Campaigns", description: "Control cadence and approvals." },
  { href: "/outreach/sequences", label: "Sequences", description: "Edit message steps and stop rules." },
  { href: "/outreach/companies-house", label: "Companies House", description: "Turn registry profiles into leads." },
  { href: "/outreach/channels", label: "Channels", description: "Content and delivery entry points." },
  { href: "/outreach/approvals", label: "Approvals", description: "Approve pending Soft Wall sends." },
] as const;

export default function OutreachOverviewPage() {
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const [leadImportText, setLeadImportText] = React.useState("");
  const [campaignName, setCampaignName] = React.useState("");
  const [campaignObjective, setCampaignObjective] = React.useState("");
  const [selectedLeadId, setSelectedLeadId] = React.useState("");
  const [selectedSequenceId, setSelectedSequenceId] = React.useState("");
  const [chQuery, setChQuery] = React.useState("");
  const [chHits, setChHits] = React.useState<CompanySearchHit[]>([]);
  const [selectedCompany, setSelectedCompany] = React.useState<CompanyProfile | null>(null);
  const [chLoading, setChLoading] = React.useState(false);

  const overview = useSWR(["outreach-overview", WORKSPACE], () => fetchOutreachOverview(WORKSPACE));
  const control = useSWR(["outreach-control", WORKSPACE], () => fetchOutreachControl(WORKSPACE));
  const schedulerHealth = useSWR(["outreach-scheduler-health", WORKSPACE], () =>
    fetchOutreachSchedulerHealth(WORKSPACE),
  );
  const leads = useSWR(["outreach-leads", WORKSPACE], () => fetchOutreachLeads(WORKSPACE));
  const sequences = useSWR(["outreach-sequences", WORKSPACE], () => fetchOutreachSequences(WORKSPACE));

  React.useEffect(() => {
    const firstLead = leads.data?.leads?.[0]?.id;
    if (!selectedLeadId && firstLead) setSelectedLeadId(firstLead);
  }, [leads.data, selectedLeadId]);

  React.useEffect(() => {
    const firstSeq = sequences.data?.sequences?.[0]?.id;
    if (!selectedSequenceId && firstSeq) setSelectedSequenceId(firstSeq);
  }, [sequences.data, selectedSequenceId]);

  const refresh = async () => {
    await Promise.all([
      overview.mutate(),
      control.mutate(),
      schedulerHealth.mutate(),
      leads.mutate(),
      sequences.mutate(),
    ]);
  };

  const run = async (fn: () => Promise<void>, success: string) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      setMessage(success);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  const onProcessDue = () => {
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        const result = await processOutreachDue(WORKSPACE, false);
        const processed = Array.isArray(result.processed)
          ? result.processed.length
          : Number(result.processed ?? 0);
        const skipped = Array.isArray(result.skipped) ? result.skipped.length : Number(result.skipped ?? 0);
        setMessage(`Queued ${processed} Soft Wall draft(s); skipped ${skipped}`);
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Request failed");
      } finally {
        setBusy(false);
      }
    })();
  };

  const onTogglePause = () =>
    void run(async () => {
      const paused = Boolean(control.data?.state?.paused);
      await patchOutreachControl(paused ? "resume" : "pause", paused ? undefined : "Operator pause from control center", WORKSPACE);
    }, control.data?.state?.paused ? "Outreach resumed" : "Outreach paused");

  const onImportLeads = () =>
    void run(async () => {
      if (!leadImportText.trim()) throw new Error("Add at least one lead line");
      await importOutreachLeads({ lines: leadImportText, csv_text: leadImportText }, WORKSPACE);
      setLeadImportText("");
    }, "Leads imported");

  const onCreateCampaign = () =>
    void run(async () => {
      if (!campaignName.trim()) throw new Error("Campaign name is required");
      await createOutreachCampaign({ name: campaignName.trim(), objective: campaignObjective.trim() || undefined }, WORKSPACE);
      setCampaignName("");
      setCampaignObjective("");
    }, "Campaign created");

  const onEnroll = () =>
    void run(async () => {
      if (!selectedLeadId || !selectedSequenceId) throw new Error("Choose a lead and a sequence");
      await enrollOutreachLead({ lead_id: selectedLeadId, sequence_id: selectedSequenceId }, WORKSPACE);
    }, "Lead enrolled in sequence");

  const onSearchCompanies = async () => {
    if (!chQuery.trim()) {
      setError("Enter a company name or number");
      return;
    }
    setChLoading(true);
    setError(null);
    try {
      const result = await searchCompaniesHouse(chQuery.trim(), { items_per_page: 6 });
      setChHits(result.items ?? []);
      if (result.items?.[0]?.company_number) {
        setSelectedCompany(await fetchCompanyProfile(result.items[0].company_number));
      } else {
        setSelectedCompany(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Companies House search failed");
    } finally {
      setChLoading(false);
    }
  };

  const onImportCompany = () =>
    void run(async () => {
      if (!selectedCompany) throw new Error("Select a company first");
      await importCompaniesHouseLead(
        {
          company_number: selectedCompany.company_number,
          company_name: selectedCompany.company_name || selectedCompany.company_number,
          tags: ["companies_house"],
          company_status: selectedCompany.company_status || undefined,
          registered_office: selectedCompany.registered_office_address?.formatted || undefined,
          sic_codes: selectedCompany.sic_codes,
          officer_names: (selectedCompany.officers ?? []).map((o) => o.name).filter(Boolean) as string[],
        },
        WORKSPACE,
      );
    }, "Company imported as lead");

  const summary = overview.data?.summary ?? overview.data?.pipeline ?? {};
  const loading = overview.isLoading && !overview.data;

  return (
    <Stack spacing={3}>
      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <ControlCenter
        control={control.data?.state ?? null}
        schedulerHealth={schedulerHealth.data ?? null}
        busy={busy}
        onProcessDue={onProcessDue}
        onTogglePause={onTogglePause}
      />

      {loading ? (
        <Typography color="text.secondary">Loading outreach...</Typography>
      ) : (
        <MetricCards overview={overview.data ?? null} />
      )}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
                <Box>
                  <Typography variant="subtitle1">Import leads</Typography>
                  <Typography variant="caption" color="text.secondary">
                    One lead per line: name | email | company | phone
                  </Typography>
                </Box>
                <Button size="small" variant="contained" disabled={busy} onClick={onImportLeads}>
                  Import
                </Button>
              </Stack>
              <TextField
                fullWidth
                multiline
                minRows={4}
                sx={{ mt: 2 }}
                value={leadImportText}
                onChange={(e) => setLeadImportText(e.target.value)}
                placeholder="Jane Doe | jane@example.com | Example Ltd | +44..."
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
                <Box>
                  <Typography variant="subtitle1">Create campaign</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Build a new campaign from the home screen.
                  </Typography>
                </Box>
                <Button size="small" variant="contained" disabled={busy} onClick={onCreateCampaign}>
                  Create
                </Button>
              </Stack>
              <Stack spacing={1.5} sx={{ mt: 2 }}>
                <TextField
                  size="small"
                  fullWidth
                  label="Campaign name"
                  value={campaignName}
                  onChange={(e) => setCampaignName(e.target.value)}
                />
                <TextField
                  size="small"
                  fullWidth
                  label="Objective"
                  value={campaignObjective}
                  onChange={(e) => setCampaignObjective(e.target.value)}
                />
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
                <Box>
                  <Typography variant="subtitle1">Enroll a sequence</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Pick a lead and a sequence, then enroll directly.
                  </Typography>
                </Box>
                <Button size="small" variant="contained" disabled={busy} onClick={onEnroll}>
                  Enroll
                </Button>
              </Stack>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mt: 2 }}>
                <FormControl size="small" fullWidth>
                  <InputLabel id="enroll-lead">Lead</InputLabel>
                  <Select
                    labelId="enroll-lead"
                    label="Lead"
                    value={selectedLeadId}
                    onChange={(e) => setSelectedLeadId(e.target.value)}
                  >
                    {(leads.data?.leads ?? []).map((lead) => (
                      <MenuItem key={lead.id} value={lead.id}>
                        {lead.name}
                        {lead.company ? ` - ${lead.company}` : ""}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" fullWidth>
                  <InputLabel id="enroll-seq">Sequence</InputLabel>
                  <Select
                    labelId="enroll-seq"
                    label="Sequence"
                    value={selectedSequenceId}
                    onChange={(e) => setSelectedSequenceId(e.target.value)}
                  >
                    {(sequences.data?.sequences ?? []).map((seq) => (
                      <MenuItem key={seq.id} value={seq.id}>
                        {seq.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Stack>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1.5, display: "block" }}>
                {leads.data?.count ?? 0} leads loaded, {sequences.data?.count ?? 0} sequences loaded
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
                <Box>
                  <Typography variant="subtitle1">Companies House ingest</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Search, inspect, and import a public company as a lead.
                  </Typography>
                </Box>
                <Button size="small" variant="contained" disabled={chLoading} onClick={() => void onSearchCompanies()}>
                  {chLoading ? "Searching..." : "Search"}
                </Button>
              </Stack>
              <TextField
                size="small"
                fullWidth
                sx={{ mt: 2 }}
                label="Company name or number"
                value={chQuery}
                onChange={(e) => setChQuery(e.target.value)}
              />
              <Stack spacing={1} sx={{ mt: 1.5 }}>
                {chHits.slice(0, 3).map((hit) => (
                  <Button
                    key={hit.company_number}
                    variant="outlined"
                    size="small"
                    sx={{ justifyContent: "flex-start", textAlign: "left", py: 1 }}
                    onClick={() =>
                      void fetchCompanyProfile(hit.company_number).then(setSelectedCompany).catch((err) => {
                        setError(err instanceof Error ? err.message : "Profile load failed");
                      })
                    }
                  >
                    <Box>
                      <Typography variant="body2">{hit.title || hit.company_number}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {hit.company_number}
                        {hit.address_snippet ? ` - ${hit.address_snippet}` : ""}
                      </Typography>
                    </Box>
                  </Button>
                ))}
              </Stack>
              {selectedCompany ? (
                <Box sx={{ mt: 1.5, p: 1.5, border: 1, borderColor: "divider", borderRadius: 1 }}>
                  <Typography variant="body2" fontWeight={600}>
                    {selectedCompany.company_name || selectedCompany.company_number}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block">
                    {selectedCompany.company_status || "unknown"}
                    {selectedCompany.registered_office_address?.formatted
                      ? ` - ${selectedCompany.registered_office_address.formatted}`
                      : ""}
                  </Typography>
                  <Button size="small" sx={{ mt: 1 }} variant="contained" disabled={busy} onClick={onImportCompany}>
                    Add as lead
                  </Button>
                </Box>
              ) : null}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Pipeline snapshot
          </Typography>
          <Grid container spacing={1}>
            {PIPELINE_STAGES.map((stage) => (
              <Grid key={stage} size={{ xs: 6, sm: 4, md: 3, lg: 2 }}>
                <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, px: 1.5, py: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    {pipelineLabel(stage)}
                  </Typography>
                  <Typography variant="h6">{summary[stage] ?? 0}</Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>

      {(overview.data?.defaults?.campaign || overview.data?.defaults?.sequence) && (
        <Card variant="outlined">
          <CardContent>
            <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" useFlexGap>
              <Box>
                <Typography variant="subtitle1">Operational defaults</Typography>
                <Typography variant="caption" color="text.secondary">
                  Default campaign and sequence that seeds new work.
                </Typography>
              </Box>
              <Stack direction="row" spacing={1}>
                <Button size="small" variant="outlined" component="a" href="/outreach/campaigns">
                  Edit campaigns
                </Button>
                <Button size="small" variant="outlined" component="a" href="/outreach/sequences">
                  Edit sequences
                </Button>
              </Stack>
            </Stack>
            <Grid container spacing={1.5} sx={{ mt: 1 }}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, px: 1.5, py: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Default campaign
                  </Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {overview.data?.defaults?.campaign?.name ?? "Not set"}
                  </Typography>
                </Box>
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, px: 1.5, py: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Default sequence
                  </Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {overview.data?.defaults?.sequence?.name ?? "Not set"}
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          Quick actions
        </Typography>
        <Grid container spacing={1.5}>
          {QUICK_LINKS.map((item) => (
            <Grid key={item.href} size={{ xs: 12, sm: 6, md: 4 }}>
              <Card variant="outlined">
                <CardActionArea component="a" href={item.href}>
                  <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                    <Typography variant="body2" fontWeight={600}>
                      {item.label}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.description}
                    </Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            How this works
          </Typography>
          <Typography component="ol" variant="body2" color="text.secondary" sx={{ pl: 2, m: 0 }}>
            <li>Import or add leads, then route them into campaigns and lists.</li>
            <li>Enroll leads into sequences, then queue due steps through the Soft Wall.</li>
            <li>Review replies, bookings, and approvals from the same workspace.</li>
            <li>Use Companies House to turn public records into leads when needed.</li>
          </Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
