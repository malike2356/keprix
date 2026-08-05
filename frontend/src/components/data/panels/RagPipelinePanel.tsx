"use client";

import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
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
  const [pipelineId, setPipelineId] = React.useState("production-default");
  const [defaultPipelineId, setDefaultPipelineId] = React.useState("production-default");
  const [refreshKey, setRefreshKey] = React.useState(0);
  const [tab, setTab] = React.useState(0);

  React.useEffect(() => {
    fetchRagConfig()
      .then((cfg) => {
        if (cfg.default_pipeline_id) {
          setDefaultPipelineId(cfg.default_pipeline_id);
          setPipelineId((prev) => (prev === "production-default" ? cfg.default_pipeline_id : prev));
        }
      })
      .catch(() => null);
  }, []);

  return (
    <Box>
      <Tabs value={tab} onChange={(_e, next) => setTab(next)} sx={{ mb: 2 }}>
        <Tab label="Pipelines" />
        <Tab label="Run" />
        <Tab label="History" />
      </Tabs>
      {tab === 0 ? (
        <PipelineBuilder
          pipelineId={pipelineId}
          onPipelineIdChange={setPipelineId}
          onIngested={() => {
            setRefreshKey((value) => value + 1);
            setTab(1);
          }}
          initialSourceType={initialSourceType as "manual" | "notion" | "file" | "vault" | "url"}
          defaultPipelineId={defaultPipelineId}
        />
      ) : null}
      {tab === 1 || tab === 2 ? (
        <PipelineRunViewer key={`${refreshKey}-${tab}`} pipelineId={pipelineId} />
      ) : null}
    </Box>
  );
}
