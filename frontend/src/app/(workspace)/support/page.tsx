"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import {
  createHandoff,
  createIncident,
  createSupportTicket,
  fetchCommunityLinks,
  fetchDiagnosticsBundle,
  fetchIncidents,
  fetchSetupRescue,
  fetchSupportChecklist,
  fetchSupportTickets,
  generateIncidentPost,
  updateSupportChecklist,
} from "@/lib/support-api";

const TICKET_CATEGORIES = [
  "installation",
  "provider_setup",
  "channel",
  "billing",
  "data_import",
  "failed_job",
  "security",
  "lost_admin",
  "backup_restore",
  "bug",
  "feature_request",
];

export default function SupportPage() {
  const [tab, setTab] = React.useState(0);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const { data: checklist, mutate: mutateChecklist } = useSWR("support-checklist", fetchSupportChecklist);
  const { data: tickets, mutate: mutateTickets } = useSWR("support-tickets", fetchSupportTickets);
  const { data: incidents, mutate: mutateIncidents } = useSWR("support-incidents", fetchIncidents);
  const { data: community } = useSWR("support-community", fetchCommunityLinks);
  const { data: rescue } = useSWR("support-rescue", fetchSetupRescue);

  const [category, setCategory] = React.useState("bug");
  const [subject, setSubject] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [attachDiagnostics, setAttachDiagnostics] = React.useState(true);

  const [incidentTitle, setIncidentTitle] = React.useState("");
  const [incidentSummary, setIncidentSummary] = React.useState("");

  const runAction = async (action: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Support"
        description="Self-host help, safe diagnostics, incident notes, and customer success checklists. Community-driven; no paid support is bundled with Keprix."
      />
      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}

      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 2 }}>
        <Tab label="Checklist" />
        <Tab label="Help request" />
        <Tab label="Diagnostics" />
        <Tab label="Incidents" />
        <Tab label="Community" />
      </Tabs>

      {tab === 0 ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Customer success checklist ({checklist?.progress.percent ?? 0}%)
            </Typography>
            <List dense>
              {(checklist?.items ?? []).map((item) => (
                <ListItem key={item.id}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={item.completed}
                        onChange={(event) =>
                          void runAction(async () => {
                            await updateSupportChecklist(item.id, event.target.checked);
                            await mutateChecklist();
                          })
                        }
                      />
                    }
                    label={item.label}
                  />
                </ListItem>
              ))}
            </List>
            <Typography variant="subtitle2" sx={{ mt: 2 }}>
              Setup rescue
            </Typography>
            <List dense>
              {(rescue?.steps ?? []).map((step: { id: string; title: string; detail: string }) => (
                <ListItem key={step.id}>
                  <ListItemText primary={step.title} secondary={step.detail} />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      ) : null}

      {tab === 1 ? (
        <Card variant="outlined">
          <CardContent sx={{ display: "grid", gap: 2 }}>
            <TextField select label="Category" value={category} onChange={(e) => setCategory(e.target.value)}>
              {TICKET_CATEGORIES.map((value) => (
                <MenuItem key={value} value={value}>
                  {value}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} fullWidth />
            <TextField
              label="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              multiline
              minRows={4}
              fullWidth
            />
            <FormControlLabel
              control={<Checkbox checked={attachDiagnostics} onChange={(e) => setAttachDiagnostics(e.target.checked)} />}
              label="Attach redacted diagnostics bundle"
            />
            <Button
              variant="contained"
              disabled={busy || !subject.trim() || !description.trim()}
              onClick={() =>
                void runAction(async () => {
                  await createSupportTicket({
                    category,
                    subject: subject.trim(),
                    description: description.trim(),
                    attach_diagnostics: attachDiagnostics,
                  });
                  setSubject("");
                  setDescription("");
                  setMessage("Help request saved. Export from API or share diagnostics separately.");
                  await mutateTickets();
                })
              }
            >
              Submit help request
            </Button>
            <Button
              variant="outlined"
              disabled={busy}
              onClick={() =>
                void runAction(async () => {
                  await createHandoff({
                    category,
                    summary: subject.trim() || description.trim(),
                    privacy: attachDiagnostics ? "standard" : "minimal",
                  });
                  setMessage("Human handoff recorded with selected privacy level.");
                })
              }
            >
              Request human handoff
            </Button>
            <List dense>
              {(tickets?.tickets ?? []).slice(0, 5).map((ticket) => (
                <ListItem key={ticket.id}>
                  <ListItemText
                    primary={ticket.subject}
                    secondary={`${ticket.category} · ${ticket.status} · ${ticket.created_at}`}
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      ) : null}

      {tab === 2 ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Diagnostics bundles redact secrets and omit private messages. Safe to attach to community issues.
            </Typography>
            <Button
              variant="contained"
              disabled={busy}
              onClick={() =>
                void runAction(async () => {
                  const bundle = await fetchDiagnosticsBundle();
                  const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
                  const url = URL.createObjectURL(blob);
                  const anchor = document.createElement("a");
                  anchor.href = url;
                  anchor.download = "keprix-diagnostics.json";
                  anchor.click();
                  URL.revokeObjectURL(url);
                  setMessage("Diagnostics bundle downloaded.");
                })
              }
            >
              Download diagnostics bundle
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {tab === 3 ? (
        <Card variant="outlined">
          <CardContent sx={{ display: "grid", gap: 2 }}>
            <TextField label="Incident title" value={incidentTitle} onChange={(e) => setIncidentTitle(e.target.value)} />
            <TextField
              label="Summary"
              value={incidentSummary}
              onChange={(e) => setIncidentSummary(e.target.value)}
              multiline
              minRows={3}
              fullWidth
            />
            <Button
              variant="contained"
              disabled={busy || !incidentTitle.trim() || !incidentSummary.trim()}
              onClick={() =>
                void runAction(async () => {
                  const created = await createIncident({
                    title: incidentTitle.trim(),
                    severity: "medium",
                    summary: incidentSummary.trim(),
                  });
                  const post = await generateIncidentPost(created.incident.id);
                  setMessage("Incident created and public post draft generated.");
                  setIncidentTitle("");
                  setIncidentSummary("");
                  navigator.clipboard.writeText(post.public_post).catch(() => undefined);
                  await mutateIncidents();
                })
              }
            >
              Create incident and generate post
            </Button>
            <List dense>
              {(incidents?.incidents ?? []).map((incident) => (
                <ListItem key={incident.id}>
                  <ListItemText
                    primary={incident.title}
                    secondary={`${incident.severity} · ${incident.status}`}
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      ) : null}

      {tab === 4 ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="body2" sx={{ mb: 2 }}>
              Keprix is MIT-licensed self-host software. Use community channels below; commercial managed support is a
              separate product from any SaaS vendor.
            </Typography>
            <List>
              {(community?.links ?? []).map((link: { label: string; url: string }) => (
                <ListItem key={link.url} component="a" href={link.url} target="_blank" rel="noopener noreferrer">
                  <ListItemText primary={link.label} secondary={link.url} />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      ) : null}
    </Box>
  );
}
