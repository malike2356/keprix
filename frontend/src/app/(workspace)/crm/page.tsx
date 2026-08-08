"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid2";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import useSWR from "swr";
import CrmSoftWallPanel from "@/components/crm/CrmSoftWallPanel";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { fetchCrmFunnel, fetchCrmKillSwitches, fetchCrmStatus } from "@/lib/crm-api";

const QUICK_LINKS = [
  { href: "/crm/pipeline", label: "Pipeline board", description: "Kanban by canonical CRM stage." },
  { href: "/crm/workflows", label: "Workflows", description: "Canvas builder, validate, simulate, publish." },
  { href: "/crm/analytics", label: "Analytics", description: "Semantic funnel, guards, and drill-down." },
  { href: "/crm/ops", label: "Ops centre", description: "Live runs, approvals, alerts, kill switches." },
  { href: "/crm/leads", label: "Leads", description: "Review and edit CRM leads." },
  { href: "/crm/contacts", label: "Contacts", description: "People with email or phone." },
  { href: "/crm/accounts", label: "Accounts", description: "Companies and organisations." },
  { href: "/crm/deals", label: "Deals", description: "Opportunities toward paying." },
  { href: "/crm/lists", label: "Lists", description: "Named sets for review and enroll." },
  { href: "/crm/jobs", label: "Jobs", description: "Discovery and enrich history." },
  { href: "/crm/inbox", label: "Inbox", description: "Replies, stage suggestions, takeover, complaints." },
  { href: "/crm/deliverability", label: "Deliverability", description: "Sender readiness, bounce and complaint rates." },
  { href: "/crm/outbox", label: "Outbox", description: "Pending, failed, and dead-letter sends." },
  { href: "/crm/merges", label: "Merges", description: "Identity merge Soft Wall suggestions." },
  { href: "/crm/contactability", label: "Contactability", description: "Allow, deny, or needs_review decisions." },
  { href: "/crm/settings", label: "Settings", description: "Kill switches, cadence caps, policy notes." },
  { href: "/crm/enrich", label: "Enrich", description: "Sheet preprocess upload, map, Soft Wall apply." },
  { href: "/crm/discover", label: "Discover", description: "Find companies and run discovery adapters." },
  { href: "/crm/suppressions", label: "Suppressions", description: "Suppression manager; always wins over consent." },
  { href: "/outreach", label: "Soft Wall outreach", description: "Sequences, campaigns, send approvals." },
  { href: "/leads", label: "Legacy leads", description: "Deep-link to the older leads surface." },
] as const;

const FUNNEL_KEYS = [
  { key: "lists_created", label: "Lists" },
  { key: "leads_discovered", label: "Discovered" },
  { key: "enrolled", label: "Enrolled" },
  { key: "replied", label: "Replied" },
  { key: "booked", label: "Booked" },
  { key: "customers", label: "Customers" },
  { key: "paying", label: "Paying" },
  { key: "unsubscribes", label: "Unsubs" },
] as const;

export default function CrmOverviewPage() {
  const status = useSWR(["crm-status", CRM_WORKSPACE], () => fetchCrmStatus(CRM_WORKSPACE));
  const funnel = useSWR(["crm-funnel", CRM_WORKSPACE], () => fetchCrmFunnel(CRM_WORKSPACE));
  const kills = useSWR(["crm-kills-overview", CRM_WORKSPACE], () => fetchCrmKillSwitches(CRM_WORKSPACE));
  const counts = status.data?.counts;
  const metrics = funnel.data?.metrics;
  const loading = (status.isLoading && !status.data) || (funnel.isLoading && !funnel.data);
  const workspaceKillOn = (kills.data?.items || []).some(
    (k) => String(k.scope) === "workspace" && Boolean(k.enabled),
  );
  const loadError = status.error || funnel.error;

  return (
    <Stack spacing={3}>
      {status.error || funnel.error ? (
        <Alert severity="error">
          Could not load CRM overview
          {loadError ? `: ${loadError instanceof Error ? loadError.message : String(loadError)}` : null}
        </Alert>
      ) : null}

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          Funnel snapshot
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Live funnel KPIs for this workspace. Empty workspaces show zeros; no demo data.
        </Typography>
        {workspaceKillOn ? (
          <Alert severity="error" sx={{ mb: 1.5 }}>
            Workspace kill switch is ON (outreach paused).{" "}
            <Typography component={Link} href="/crm/settings" color="inherit" sx={{ textDecoration: "underline" }}>
              Open settings
            </Typography>{" "}
            (resume is Soft Wall gated).
          </Alert>
        ) : null}
        {funnel.data?.deliverability_strip?.soft_wall_block_cold_send ? (
          <Alert severity="warning" sx={{ mb: 1.5 }}>
            Deliverability gate active.{" "}
            <Typography component={Link} href="/crm/deliverability" color="inherit" sx={{ textDecoration: "underline" }}>
              Open deliverability
            </Typography>
          </Alert>
        ) : null}
        {loading ? (
          <Typography color="text.secondary">Loading CRM status...</Typography>
        ) : (
          <Grid container spacing={1.5}>
            {FUNNEL_KEYS.map((metric) => (
              <Grid key={metric.key} size={{ xs: 6, sm: 4, md: 3 }}>
                <Card variant="outlined">
                  <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                    <Typography variant="caption" color="text.secondary">
                      {metric.label}
                    </Typography>
                    <Typography variant="h5" sx={{ mt: 0.5 }}>
                      {metrics ? metrics[metric.key] ?? 0 : 0}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
            <Grid size={{ xs: 6, sm: 4, md: 3 }}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                  <Typography variant="caption" color="text.secondary">
                    Pending Soft Wall
                  </Typography>
                  <Typography variant="h5" sx={{ mt: 0.5 }}>
                    {counts?.pending_approvals ?? 0}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 6, sm: 4, md: 3 }}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                  <Typography variant="caption" color="text.secondary">
                    Enrichment cost
                  </Typography>
                  <Typography variant="h5" sx={{ mt: 0.5 }}>
                    {metrics?.enrichment_cost ?? 0}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}
      </Box>

      <CrmSoftWallPanel />

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          CRM surfaces
        </Typography>
        <Grid container spacing={1.5}>
          {QUICK_LINKS.map((item) => (
            <Grid key={item.href} size={{ xs: 12, sm: 6, md: 4 }}>
              <Card variant="outlined">
                <CardActionArea component={Link} href={item.href}>
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
    </Stack>
  );
}
