"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import { useParams } from "next/navigation";
import * as React from "react";
import OpportunityApprovalQueue from "@/components/opportunity/OpportunityApprovalQueue";
import OpportunityArtifactViewer from "@/components/opportunity/OpportunityArtifactViewer";
import OpportunityIntegrationStatus from "@/components/opportunity/OpportunityIntegrationStatus";
import OpportunityScoreCard from "@/components/opportunity/OpportunityScoreCard";
import OpportunityStatusBadge from "@/components/opportunity/OpportunityStatusBadge";
import OpportunityTimeline from "@/components/opportunity/OpportunityTimeline";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import {
  archiveOpportunity,
  fetchOpportunity,
  fetchOpportunityArtifact,
  fetchOpportunityAsset,
  OPPORTUNITY_STATUSES,
  pauseOpportunity,
  runOpportunityPhase,
  runOpportunityPipeline,
  type OpportunityDetail,
} from "@/lib/opportunity-api";

const TABS = ["Artifacts", "Score", "Assets", "Launch", "Approvals", "Growth"] as const;

export default function OpportunityDetailPage() {
  const params = useParams<{ id: string }>();
  const opportunityId = params.id;
  const [tab, setTab] = React.useState(0);
  const [detail, setDetail] = React.useState<OpportunityDetail | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [assetContent, setAssetContent] = React.useState("");
  const [launchContent, setLaunchContent] = React.useState("");
  const [growthContent, setGrowthContent] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    const row = await fetchOpportunity(opportunityId);
    setDetail(row);
    try {
      const launch = await fetchOpportunityArtifact(opportunityId, "11-launch-plan.md");
      setLaunchContent(launch.content);
    } catch {
      setLaunchContent("");
    }
    try {
      const growth = await fetchOpportunityArtifact(opportunityId, "14-growth-loop.md");
      setGrowthContent(growth.content);
    } catch {
      setGrowthContent("");
    }
    try {
      const asset = await fetchOpportunityAsset(opportunityId, "landing-page.md");
      setAssetContent(asset.content);
    } catch {
      setAssetContent("");
    }
    setLoading(false);
  }, [opportunityId]);

  React.useEffect(() => {
    load().catch((err) => {
      setError(err instanceof Error ? err.message : "Load failed");
      setLoading(false);
    });
  }, [load]);

  const runPipeline = async () => {
    setBusy(true);
    setError(null);
    try {
      await runOpportunityPipeline(opportunityId, { pause_on_approval: true });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setBusy(false);
    }
  };

  const runPhase = async (phase: string) => {
    setBusy(true);
    setError(null);
    try {
      await runOpportunityPhase(opportunityId, phase);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Phase failed");
    } finally {
      setBusy(false);
    }
  };

  if (loading && !detail) {
    return (
      <Box sx={{ p: { xs: 2, md: 3 }, maxWidth: 1200, mx: "auto" }}>
        <SkeletonDetailPanel fields={6} />
      </Box>
    );
  }

  if (!detail) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="error">{error || "Opportunity not found"}</Typography>
      </Box>
    );
  }

  const meta = detail.meta;
  const pending = meta.pending_approvals ?? [];

  return (
    <Box sx={{ p: { xs: 2, md: 3 }, maxWidth: 1200, mx: "auto" }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Box>
          <Typography variant="h5">{detail.record.title}</Typography>
          <Typography variant="caption" color="text.secondary">
            {opportunityId}
          </Typography>
        </Box>
        <OpportunityStatusBadge status={meta.status} labels={OPPORTUNITY_STATUSES} />
      </Stack>

      <OpportunityTimeline
        completedPhases={meta.completed_phases}
        currentPhase={meta.current_phase}
      />

      <Stack direction="row" spacing={1} sx={{ my: 2, flexWrap: "wrap" }}>
        <Button size="small" variant="contained" disabled={busy} onClick={runPipeline}>
          Run playbooks
        </Button>
        <Button size="small" variant="outlined" disabled={busy} onClick={() => runPhase("launch_orchestrator")}>
          Prepare launch (dry run)
        </Button>
        <Button size="small" variant="outlined" disabled={busy} onClick={() => pauseOpportunity(opportunityId).then(load)}>
          Pause
        </Button>
        <Button size="small" variant="outlined" disabled={busy} onClick={() => archiveOpportunity(opportunityId).then(load)}>
          Archive
        </Button>
      </Stack>

      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}

      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 2 }}>
        {TABS.map((label) => (
          <Tab key={label} label={label} />
        ))}
      </Tabs>

      {tab === 0 ? <OpportunityArtifactViewer opportunityId={opportunityId} /> : null}
      {tab === 1 ? (
        <OpportunityScoreCard
          overallScore={meta.validation?.overall_score}
          recommendation={meta.validation?.recommendation}
          growthStatus={meta.growth_status}
        />
      ) : null}
      {tab === 2 ? (
        <Box component="pre" sx={{ whiteSpace: "pre-wrap", fontSize: 12, p: 2, border: 1, borderColor: "divider" }}>
          {assetContent || "No asset drafts yet. Run the asset_factory playbook."}
        </Box>
      ) : null}
      {tab === 3 ? (
        <Box component="pre" sx={{ whiteSpace: "pre-wrap", fontSize: 12, p: 2, border: 1, borderColor: "divider" }}>
          {launchContent || "No launch plan yet. Run launch_orchestrator playbook."}
        </Box>
      ) : null}
      {tab === 4 ? (
        <OpportunityApprovalQueue opportunityId={opportunityId} approvals={pending} onUpdated={load} />
      ) : null}
      {tab === 5 ? (
        <Box component="pre" sx={{ whiteSpace: "pre-wrap", fontSize: 12, p: 2, border: 1, borderColor: "divider" }}>
          {growthContent || "No growth loop report yet. Run growth_loop playbook."}
        </Box>
      ) : null}

      {tab === 3 || tab === 4 ? (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Integrations
          </Typography>
          <OpportunityIntegrationStatus integrationsConfig={meta.integrations_config} />
        </Box>
      ) : null}
    </Box>
  );
}
