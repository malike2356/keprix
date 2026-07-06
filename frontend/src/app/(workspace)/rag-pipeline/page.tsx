"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import PipelineBuilder from "@/components/rag/PipelineBuilder";
import PipelineRunViewer from "@/components/rag/PipelineRunViewer";

export default function RagPipelinePage() {
  const searchParams = useSearchParams();
  const initialSourceType = searchParams.get("source") === "notion" ? "notion" : "manual";
  const [pipelineId, setPipelineId] = React.useState("production-default");
  const [refreshKey, setRefreshKey] = React.useState(0);

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">RAG Pipelines</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Haystack-style modular pipelines with routing, citations, evaluation, and playbook tracing.
        </p>
      </div>
      <PipelineBuilder
        pipelineId={pipelineId}
        onPipelineIdChange={setPipelineId}
        onIngested={() => setRefreshKey((value) => value + 1)}
        initialSourceType={initialSourceType}
      />
      <PipelineRunViewer key={refreshKey} pipelineId={pipelineId} />
    </div>
  );
}
