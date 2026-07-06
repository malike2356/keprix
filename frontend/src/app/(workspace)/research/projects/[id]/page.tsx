"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid2";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import CitationPicker from "@/components/research/CitationPicker";
import CodebookPanel from "@/components/research/CodebookPanel";
import DatasetManager from "@/components/research/DatasetManager";
import LinkedNotesPanel from "@/components/research/LinkedNotesPanel";
import ObsidianVaultSettings from "@/components/research/ObsidianVaultSettings";
import ResearchGettingStarted from "@/components/research/ResearchGettingStarted";
import ResearchPlaybookRunner from "@/components/research/ResearchPlaybookRunner";
import ResearchStatsPanel from "@/components/research/ResearchStatsPanel";
import ResearchTimeline from "@/components/research/ResearchTimeline";
import ZoteroSettings from "@/components/research/ZoteroSettings";
import { exportResearchObsidian, fetchResearchProject, type ResearchProject } from "@/lib/research-workspace-api";

function bucketObjects(objects: Array<Record<string, unknown>>, objectType: string) {
  return objects.filter((item) => item.object_type === objectType);
}

export default function ResearchProjectPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [project, setProject] = React.useState<ResearchProject | null>(null);
  const [objects, setObjects] = React.useState<Array<Record<string, unknown>>>([]);
  const [vaultId, setVaultId] = React.useState<string | null>(null);
  const [datasetId, setDatasetId] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [exportMessage, setExportMessage] = React.useState<string | null>(null);

  const exportObsidian = React.useCallback(async () => {
    if (!projectId) return;
    try {
      const result = await exportResearchObsidian(projectId);
      setExportMessage(`Exported ${result.files} file(s) to Obsidian.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Obsidian export failed");
    }
  }, [projectId]);

  const refresh = React.useCallback(() => {
    if (!projectId) return;
    fetchResearchProject(projectId)
      .then((payload) => {
        setProject(payload.project);
        setObjects(payload.objects || []);
      })
      .catch((err: Error) => setError(err.message));
  }, [projectId]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const sources = bucketObjects(objects, "source");
  const datasets = bucketObjects(objects, "dataset");
  const analyses = objects.filter((item) =>
    ["analysis_run", "statistical_output", "notebook_run", "playbook_run"].includes(String(item.object_type)),
  );
  const reports = bucketObjects(objects, "report_draft");
  const evidence = bucketObjects(objects, "evidence_bundle");
  const playbookRuns = bucketObjects(objects, "playbook_run");
  const pendingApprovals = playbookRuns.flatMap((run) => {
    const payload = (run.payload as Record<string, unknown>) || {};
    return (payload.pending_approvals as string[]) || [];
  });

  return (
    <Box>
      <PageHeader
        title={project?.title || "Research project"}
        description={project?.question || "Sources, playbooks, datasets, and evidence."}
        breadcrumbs={[
          { label: "Research", href: "/research" },
          { label: project?.title || projectId, href: `/research/projects/${projectId}` },
        ]}
      />
      {error ? (
        <Typography color="error" variant="body2" sx={{ mb: 2 }}>
          {error}
        </Typography>
      ) : null}
      {project ? (
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
          trace {project.trace_id} | sensitivity {project.sensitivity_level} | export {project.export_policy}
        </Typography>
      ) : null}

      {exportMessage ? (
        <Typography variant="body2" color="success.main" sx={{ mb: 2 }}>
          {exportMessage}
        </Typography>
      ) : null}

      <ResearchGettingStarted
        projectId={projectId}
        hasDataset={Boolean(datasetId || datasets.length)}
        hasVault={Boolean(vaultId)}
        onExportObsidian={() => void exportObsidian()}
      />

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Sources
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {sources.length ? `${sources.length} tracked source(s)` : "No sources yet."}
              </Typography>
              <ZoteroSettings projectId={projectId} onConnected={refresh} />
              <CitationPicker projectId={projectId} vaultId={vaultId} />
            </CardContent>
          </Card>
          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Notes
              </Typography>
              <ObsidianVaultSettings projectId={projectId} onVaultSelected={setVaultId} onExported={refresh} />
              <LinkedNotesPanel projectId={projectId} vaultId={vaultId} />
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Datasets
              </Typography>
              <DatasetManager projectId={projectId} onImported={(id) => { setDatasetId(id); refresh(); }} />
              <Box sx={{ mt: 2 }}>
                <ResearchStatsPanel datasetId={datasetId} onComplete={refresh} />
              </Box>
              <Box sx={{ mt: 2 }}>
                <CodebookPanel datasetId={datasetId} />
              </Box>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                {datasets.length ? `${datasets.length} dataset object(s)` : "No datasets registered."}
              </Typography>
            </CardContent>
          </Card>
          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Playbook runs
              </Typography>
              <ResearchPlaybookRunner projectId={projectId} onRunComplete={refresh} />
              <Box sx={{ mt: 2 }}>
                <ResearchTimeline objects={objects} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Analyses
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {analyses.length ? `${analyses.length} analysis artifact(s)` : "No analyses yet."}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Reports
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {reports.length ? `${reports.length} report draft(s)` : "No reports yet."}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Evidence map
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {evidence.length ? `${evidence.length} evidence bundle(s)` : "No bundles yet."}
              </Typography>
              <ButtonLink href={`/research?project=${projectId}`} />
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Pending approvals
              </Typography>
              {pendingApprovals.length ? (
                <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                  {pendingApprovals.map((stepId) => (
                    <Chip key={stepId} color="warning" label={stepId} />
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No playbook steps waiting for human review.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

function ButtonLink({ href }: { href: string }) {
  return (
    <Typography component={Link} href={href} variant="body2">
      Open research workspace
    </Typography>
  );
}
