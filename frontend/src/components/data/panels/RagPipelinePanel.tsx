"use client";

import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import * as React from "react";
import { useSearchParams } from "next/navigation";
import PipelineBuilder from "@/components/rag/PipelineBuilder";
import PipelineRunViewer from "@/components/rag/PipelineRunViewer";
import { fetchRagConfig } from "@/lib/rag-pipeline-api";

export default function RagPipelinePanel() {
  const searchParams = useSearchParams();
  const initialSourceType =
    searchParams.get("source") === "notion"
      ? "notion"
      : searchParams.get("source") === "url"
        ? "url"
        : searchParams.get("source") === "vault"
          ? "vault"
          : "manual";
  const [pipelineId, setPipelineId] = React.useState("");
  const [defaultPipelineId, setDefaultPipelineId] = React.useState("");
  const [pipelines, setPipelines] = React.useState<string[]>([]);
  const [configError, setConfigError] = React.useState<string | null>(null);
  const [configLoading, setConfigLoading] = React.useState(true);
  const [refreshKey, setRefreshKey] = React.useState(0);
  const [tab, setTab] = React.useState(0);

  const reloadConfig = React.useCallback(async () => {
    setConfigLoading(true);
    setConfigError(null);
    try {
      const cfg = await fetchRagConfig();
      const def = cfg.default_pipeline_id || "";
      const ids = Array.from(new Set([...(cfg.pipelines || []), def].filter(Boolean)));
      setDefaultPipelineId(def);
      setPipelines(ids);
      setPipelineId((prev) => {
        if (prev && ids.includes(prev)) return prev;
        return def || ids[0] || prev || "";
      });
    } catch (err) {
      setConfigError(err instanceof Error ? err.message : "Could not load RAG config");
    } finally {
      setConfigLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void reloadConfig();
  }, [reloadConfig]);

  return (
    <Box>
      <Tabs value={tab} onChange={(_e, next) => setTab(next)} sx={{ mb: 2 }}>
        <Tab label="Pipelines" />
        <Tab label="Run" />
        <Tab label="History" />
      </Tabs>
      {configError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {configError}
        </Alert>
      ) : null}
      {tab === 0 ? (
        <Box sx={{ display: "grid", gap: 2 }}>
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Known pipelines
            </Typography>
            {configLoading ? (
              <Typography variant="body2" color="text.secondary">
                Loading pipeline config…
              </Typography>
            ) : pipelines.length === 0 ? (
              <Alert severity="info">
                No pipelines yet. Enter an id below and create one, or set KEPRIX_RAG_DEFAULT_PIPELINE_ID.
              </Alert>
            ) : (
              <List dense disablePadding sx={{ border: 1, borderColor: "divider", borderRadius: 1, mb: 1 }}>
                {pipelines.map((id) => (
                  <ListItemButton
                    key={id}
                    selected={id === pipelineId}
                    onClick={() => {
                      setPipelineId(id);
                      setTab(1);
                    }}
                  >
                    <ListItemText
                      primary={id}
                      secondary={id === defaultPipelineId ? "default (env)" : undefined}
                    />
                  </ListItemButton>
                ))}
              </List>
            )}
          </Box>
          <PipelineBuilder
            pipelineId={pipelineId}
            onPipelineIdChange={setPipelineId}
            onIngested={() => {
              setRefreshKey((value) => value + 1);
              void reloadConfig();
              setTab(1);
            }}
            initialSourceType={initialSourceType as "manual" | "notion" | "file" | "vault" | "url"}
            defaultPipelineId={defaultPipelineId || "unset"}
            knownPipelines={pipelines}
          />
        </Box>
      ) : null}
      {tab === 1 ? (
        <PipelineRunViewer key={`run-${refreshKey}`} pipelineId={pipelineId} mode="run" />
      ) : null}
      {tab === 2 ? (
        <PipelineRunViewer
          key={`history-${refreshKey}`}
          pipelineId={pipelineId}
          mode="history"
          onReplay={(question) => {
            setTab(1);
            setRefreshKey((value) => value + 1);
            // Question restore happens inside viewer when mode=run remounts with pendingReplay via sessionStorage
            if (question) {
              try {
                sessionStorage.setItem("keprix_rag_replay_question", question);
              } catch {
                // ignore
              }
            }
          }}
        />
      ) : null}
    </Box>
  );
}
