"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { SkeletonBlock } from "@/components/ui/loading";
import { ceApi } from "@/lib/ce-api";
import { studioExportUrl } from "@/lib/playbook-studio/playbook-studio-api";
import type { StudioNodeType } from "@/lib/playbook-studio/canvas-types";
import { usePlaybookStudio } from "@/components/playbooks/studio/hooks/usePlaybookStudio";
import StudioToolbar from "@/components/playbooks/studio/StudioToolbar";
import NodePalette from "@/components/playbooks/studio/NodePalette";
import PlaybookCanvas from "@/components/playbooks/studio/PlaybookCanvas";
import NodeInspector from "@/components/playbooks/studio/NodeInspector";
import CompileErrorPanel from "@/components/playbooks/studio/CompileErrorPanel";
import VariablesPanel from "@/components/playbooks/studio/VariablesPanel";
import TemplatesPanel from "@/components/playbooks/studio/TemplatesPanel";
import CoachPanel from "@/components/playbooks/studio/CoachPanel";

type Props = {
  playbookId: string;
  connectorId?: string;
  runId?: string;
};

type RightTab = "inspector" | "errors" | "variables" | "templates";

export default function PlaybookStudioShell({ playbookId, connectorId, runId }: Props) {
  const studio = usePlaybookStudio(playbookId, connectorId, runId);
  const [rightTab, setRightTab] = React.useState<RightTab>("inspector");

  React.useEffect(() => {
    if (studio.compileErrors.length > 0) setRightTab("errors");
  }, [studio.compileErrors.length]);

  const onExportBundle = React.useCallback(async () => {
    const response = await ceApi(studioExportUrl(studio.canvas.id));
    if (!response.ok) return;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${studio.canvas.id}-export.json`;
    link.click();
    URL.revokeObjectURL(url);
  }, [studio.canvas.id]);

  const onCoachAdd = React.useCallback(
    (nodeType: StudioNodeType, data: Record<string, unknown>) => {
      const count = studio.canvas.nodes.filter((node) => node.type === nodeType).length + 1;
      const id = `${nodeType}_${count}`;
      studio.setCanvas((current) => ({
        ...current,
        nodes: [
          ...current.nodes,
          {
            id,
            type: nodeType,
            position: { x: 480, y: 320 },
            data,
          },
        ],
      }));
      studio.setSelectedNodeId(id);
    },
    [studio],
  );

  if (studio.loading) {
    return (
      <Box sx={{ p: 2 }}>
        <SkeletonBlock height={560} />
      </Box>
    );
  }

  return (
    <Box sx={{ display: "grid", gridTemplateRows: "auto auto 1fr", height: "100%", minHeight: 640 }}>
      <StudioToolbar
        id={studio.canvas.id}
        name={studio.canvas.name}
        busy={studio.busy}
        status={studio.status}
        onMetaChange={(patch) => studio.setCanvas((current) => ({ ...current, ...patch }))}
        onSave={() => void studio.save()}
        onRun={() => void studio.run()}
        onExport={() => void studio.exportYaml()}
        onExportBundle={() => void onExportBundle()}
        onImportYaml={(text) => void studio.importYaml(text)}
        onImportN8n={(workflow) => void studio.importN8n(workflow)}
        onValidate={() => void studio.validate()}
        onPublish={(options) => void studio.publish(options)}
        onAutoLayout={studio.autoLayout}
        readOnly={studio.readOnly}
      />

      {studio.readOnly ? (
        <Alert severity="info" sx={{ mx: 1, mt: 1 }}>
          Viewing run history in read-only mode. Open the playbook without a run id to edit it.
        </Alert>
      ) : null}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "220px 1fr 320px" },
          minHeight: 0,
        }}
      >
        <Box sx={{ p: 1.5, borderRight: "1px solid", borderColor: "divider", overflow: "auto" }}>
          <NodePalette />
        </Box>

        <PlaybookCanvas
          nodes={studio.canvas.nodes}
          edges={studio.canvas.edges}
          selectedNodeId={studio.selectedNodeId}
          invalidNodeIds={studio.invalidNodeIds}
          onNodesChange={studio.onNodesChange}
          onEdgesChange={studio.onEdgesChange}
          onNodesUpdate={(nodes) => studio.setCanvas((current) => ({ ...current, nodes }))}
          onEdgesUpdate={(edges) => studio.setCanvas((current) => ({ ...current, edges }))}
          onSelectNode={studio.setSelectedNodeId}
          readOnly={studio.readOnly}
        />

        <Box
          sx={{
            borderLeft: "1px solid",
            borderColor: "divider",
            overflow: "auto",
            display: "grid",
            gridTemplateRows: "auto 1fr auto",
            minHeight: 0,
          }}
        >
          <Tabs
            value={rightTab}
            onChange={(_, value: RightTab) => setRightTab(value)}
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab value="inspector" label="Inspector" />
            <Tab
              value="errors"
              label={studio.compileErrors.length ? `Errors (${studio.compileErrors.length})` : "Errors"}
            />
            <Tab value="variables" label="Variables" />
            <Tab value="templates" label="Templates" />
          </Tabs>
          <Box sx={{ overflow: "auto" }}>
            {rightTab === "inspector" ? (
              <NodeInspector node={studio.selectedNode} onUpdate={studio.updateNode} />
            ) : null}
            {rightTab === "errors" ? <CompileErrorPanel errors={studio.compileErrors} /> : null}
            {rightTab === "variables" ? (
              <Box sx={{ p: 2 }}>
                <VariablesPanel
                  variables={studio.canvas.variables || []}
                  onChange={(variables) => studio.setCanvas((current) => ({ ...current, variables }))}
                />
              </Box>
            ) : null}
            {rightTab === "templates" ? (
              <Box sx={{ p: 2 }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                  Loading a template replaces the current canvas.
                </Typography>
                <TemplatesPanel onUse={(canvas) => studio.setCanvas(canvas)} />
              </Box>
            ) : null}
          </Box>
          <CoachPanel canvas={studio.canvas} selectedNode={studio.selectedNode} onAdd={onCoachAdd} />
        </Box>
      </Box>
    </Box>
  );
}
