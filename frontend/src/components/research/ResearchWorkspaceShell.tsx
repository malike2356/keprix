"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import * as React from "react";
import ResearchProjectList from "@/components/research/ResearchProjectList";
import ObsidianVaultSettings from "@/components/research/ObsidianVaultSettings";
import LinkedNotesPanel from "@/components/research/LinkedNotesPanel";
import ZoteroSettings from "@/components/research/ZoteroSettings";
import CitationPicker from "@/components/research/CitationPicker";
import DatasetManager from "@/components/research/DatasetManager";
import CodebookPanel from "@/components/research/CodebookPanel";
import ResearchGettingStarted from "@/components/research/ResearchGettingStarted";
import ResearchStatsPanel from "@/components/research/ResearchStatsPanel";
import {
  addResearchSource,
  exportResearchObsidian,
  fetchResearchBoundary,
  fetchResearchProject,
  startResearchAnalysisRun,
  type ResearchBoundary,
  type ResearchProject,
} from "@/lib/research-workspace-api";

type Props = {
  tab: "deep" | "projects";
  deepResearchPanel: React.ReactNode;
};

export default function ResearchWorkspaceShell({ tab, deepResearchPanel }: Props) {
  const [boundary, setBoundary] = React.useState<ResearchBoundary | null>(null);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [project, setProject] = React.useState<ResearchProject | null>(null);
  const [objects, setObjects] = React.useState<Array<Record<string, unknown>>>([]);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [vaultId, setVaultId] = React.useState<string | null>(null);
  const [citationRefresh, setCitationRefresh] = React.useState(0);
  const [datasetId, setDatasetId] = React.useState<string | null>(null);

  React.useEffect(() => {
    fetchResearchBoundary()
      .then(setBoundary)
      .catch(() => setBoundary(null));
  }, []);

  React.useEffect(() => {
    if (!selectedId) {
      setProject(null);
      setObjects([]);
      return;
    }
    fetchResearchProject(selectedId)
      .then((payload) => {
        setProject(payload.project);
        setObjects(payload.objects || []);
      })
      .catch((err: Error) => setError(err.message));
  }, [selectedId]);

  const seedProject = async () => {
    if (!selectedId) return;
    setError(null);
    try {
      await addResearchSource(selectedId, {
        kind: "url",
        ref: "https://example.org/field-report",
        metadata: { title: "Field report" },
      });
      await startResearchAnalysisRun(selectedId, { tool: "jamovi", parameters: { dry_run: true } });
      const refreshed = await fetchResearchProject(selectedId);
      setProject(refreshed.project);
      setObjects(refreshed.objects || []);
      setMessage("Seeded source and queued jamovi adapter run.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Seed failed");
    }
  };

  const exportObsidian = async () => {
    if (!selectedId) return;
    setError(null);
    try {
      const result = await exportResearchObsidian(selectedId);
      setMessage(`Obsidian export prepared (${result.files} files). Open in Obsidian for graph UX.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  };

  return (
    <Box>
      {tab === "deep" ? deepResearchPanel : null}

      {tab === "projects" ? (
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { md: "320px 1fr" } }}>
          <ResearchProjectList
            selectedId={selectedId}
            onSelect={setSelectedId}
            onCreated={(created) => setProject(created)}
          />
          <Card variant="outlined">
            <CardContent>
              {boundary?.external_tools.length ? (
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                  External tools: {boundary.external_tools.join(", ")}
                </Typography>
              ) : null}
              <Typography variant="h6" gutterBottom>
                {project ? project.title : "Project workspace"}
              </Typography>
              {!project ? (
                <Typography variant="body2" color="text.secondary">
                  Select or create a research project. keprix orchestrates sources, evidence, playbooks, and exports;
                  specialist tools keep their own editors and engines.
                </Typography>
              ) : (
                <Box sx={{ display: "grid", gap: 1.5 }}>
                  <ResearchGettingStarted
                    projectId={selectedId || project.project_id}
                    hasDataset={Boolean(datasetId)}
                    hasVault={Boolean(vaultId)}
                    onExportObsidian={exportObsidian}
                  />
                  <Typography variant="body2" color="text.secondary">
                    {project.question}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    trace {project.trace_id} | sensitivity {project.sensitivity_level} | export{" "}
                    {project.export_policy}
                  </Typography>
                  <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                    <Button size="small" variant="outlined" onClick={seedProject}>
                      Seed source + analysis
                    </Button>
                    <Button size="small" variant="outlined" onClick={exportObsidian}>
                      Export to Obsidian
                    </Button>
                  </Box>
                  <ObsidianVaultSettings
                    projectId={selectedId}
                    onVaultSelected={setVaultId}
                    onExported={() => {
                      void fetchResearchProject(selectedId || project.project_id).then((payload) => {
                        setProject(payload.project);
                        setObjects(payload.objects || []);
                      });
                    }}
                  />
                  <ZoteroSettings projectId={selectedId} onConnected={() => setCitationRefresh((n) => n + 1)} />
                  <CitationPicker key={citationRefresh} projectId={selectedId} vaultId={vaultId} />
                  <DatasetManager projectId={selectedId} onImported={setDatasetId} />
                  <ResearchStatsPanel
                    datasetId={datasetId}
                    onComplete={() => {
                      void fetchResearchProject(selectedId || project.project_id).then((payload) => {
                        setObjects(payload.objects || []);
                      });
                    }}
                  />
                  <CodebookPanel datasetId={datasetId} />
                  <LinkedNotesPanel projectId={selectedId} vaultId={vaultId} />
                  <Typography variant="subtitle2">Tracked objects</Typography>
                  <Box component="ul" sx={{ m: 0, pl: 2 }}>
                    {objects.slice(0, 8).map((item) => (
                      <Typography component="li" variant="caption" key={String(item.object_id)}>
                        {String(item.object_type)}: {String(item.object_id)}
                      </Typography>
                    ))}
                    {!objects.length ? (
                      <Typography component="li" variant="caption" color="text.secondary">
                        No objects yet.
                      </Typography>
                    ) : null}
                  </Box>
                </Box>
              )}
              {message ? (
                <Typography variant="body2" sx={{ mt: 2 }}>
                  {message}
                </Typography>
              ) : null}
              {error ? (
                <Typography color="error" variant="body2" sx={{ mt: 2 }}>
                  {error}
                </Typography>
              ) : null}
            </CardContent>
          </Card>
        </Box>
      ) : null}
    </Box>
  );
}
