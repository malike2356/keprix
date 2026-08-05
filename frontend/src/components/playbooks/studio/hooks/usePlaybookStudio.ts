"use client";

import {
  applyEdgeChanges,
  applyNodeChanges,
  type EdgeChange,
  type NodeChange,
} from "@xyflow/react";
import { useRouter } from "next/navigation";
import * as React from "react";
import {
  DEFAULT_STUDIO_CANVAS,
  type StudioCanvas,
  type StudioCompileError,
  type StudioEdge,
  type StudioNode,
} from "@/lib/playbook-studio/canvas-types";
import { autoLayoutCanvas } from "@/lib/playbook-studio/autoLayout";
import {
  compileStudioCanvas,
  importN8nWorkflow,
  importYamlPlaybook,
  listStudioVersions,
  loadStudioPlaybook,
  publishStudioPlaybook,
  saveStudioCanvas,
  type StudioVersion,
} from "@/lib/playbook-studio/playbook-studio-api";
import { fetchPlaybookRunEvents, startPlaybookRun } from "@/lib/playbook-api";
import { fetchIntegration } from "@/lib/integrations-api";
import { nodeDefinition } from "@/lib/playbook-studio/node-registry";
import { mapEventsToNodeStatus } from "@/lib/playbook-studio/runOverlay";

function cloneDefault(id: string): StudioCanvas {
  return {
    ...DEFAULT_STUDIO_CANVAS,
    id: id === "new" ? "new_playbook" : id,
    nodes: DEFAULT_STUDIO_CANVAS.nodes.map((node) => ({ ...node, data: { ...node.data } })),
    edges: DEFAULT_STUDIO_CANVAS.edges.map((edge) => ({ ...edge, data: { ...edge.data } })),
  };
}

export function usePlaybookStudio(playbookId: string, connectorId?: string, runId?: string) {
  const router = useRouter();
  const [canvas, setCanvas] = React.useState<StudioCanvas>(() => cloneDefault(playbookId));
  const [selectedNodeId, setSelectedNodeId] = React.useState<string | null>("agent_task_1");
  const [compileErrors, setCompileErrors] = React.useState<StudioCompileError[]>([]);
  const [yamlPreview, setYamlPreview] = React.useState<Record<string, unknown> | null>(null);
  const [versions, setVersions] = React.useState<StudioVersion[]>([]);
  const [loading, setLoading] = React.useState(playbookId !== "new");
  const [busy, setBusy] = React.useState(false);
  const [status, setStatus] = React.useState<string | null>(null);

  React.useEffect(() => {
    let mounted = true;
    if (playbookId === "new") {
      setCanvas(cloneDefault(playbookId));
      setLoading(false);
      return;
    }
    setLoading(true);
    loadStudioPlaybook(playbookId)
      .then((payload) => {
        if (!mounted) return;
        setCanvas(payload.canvas);
        setSelectedNodeId(payload.canvas.nodes[0]?.id || null);
        void listStudioVersions(playbookId).then((items) => {
          if (mounted) setVersions(items);
        });
      })
      .catch((err) => {
        if (mounted) setStatus(err instanceof Error ? err.message : "Failed to load playbook");
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [playbookId]);

  React.useEffect(() => {
    if (!connectorId || loading) return;
    let mounted = true;
    fetchIntegration(connectorId)
      .then((item) => {
        if (!mounted) return;
        const sample = item.connector.sample_playbook_node || {};
        const type = sample.type === "http" ? "http" : "agent_task";
        const data = {
          ...nodeDefinition(type).defaults,
          ...((sample.data as Record<string, unknown> | undefined) || {}),
          connector_id: item.connector.id,
        } as StudioNode["data"];
        setCanvas((current) => {
          if (current.nodes.some((node) => node.data.connector_id === item.connector.id)) {
            return current;
          }
          const base = `${type}_${item.connector.id}`.replace(/[^a-z0-9_]/g, "_");
          let id = base;
          let index = 1;
          while (current.nodes.some((node) => node.id === id)) {
            index += 1;
            id = `${base}_${index}`;
          }
          return {
            ...current,
            nodes: [
              ...current.nodes,
              {
                id,
                type,
                position: { x: 520, y: 260 },
                data,
              },
            ],
          };
        });
        setStatus(`Added ${item.connector.label} sample node`);
      })
      .catch((err) => {
        if (mounted) setStatus(err instanceof Error ? err.message : "Failed to load connector");
      });
    return () => {
      mounted = false;
    };
  }, [connectorId, loading]);

  React.useEffect(() => {
    if (!runId) return;
    let mounted = true;
    const load = async () => {
      const payload = await fetchPlaybookRunEvents(runId);
      if (!mounted) return;
      setCanvas((current) => {
        const statuses = mapEventsToNodeStatus(payload.events, current.nodes.map((node) => node.id));
        return {
          ...current,
          nodes: current.nodes.map((node) => ({
            ...node,
            data: { ...node.data, runStatus: statuses[node.id] },
          })),
        };
      });
    };
    void load();
    const interval = window.setInterval(() => void load(), 2000);
    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, [runId]);

  const onNodesChange = React.useCallback((changes: NodeChange[]) => {
    setCanvas((current) => ({
      ...current,
      nodes: applyNodeChanges(changes, current.nodes as never) as StudioNode[],
    }));
  }, []);

  const onEdgesChange = React.useCallback((changes: EdgeChange[]) => {
    setCanvas((current) => ({
      ...current,
      edges: applyEdgeChanges(changes, current.edges as never) as StudioEdge[],
    }));
  }, []);

  const updateNode = React.useCallback((nodeId: string, data: Partial<StudioNode["data"]>) => {
    setCanvas((current) => ({
      ...current,
      nodes: current.nodes.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, ...data } } : node,
      ),
    }));
  }, []);

  const validate = React.useCallback(async () => {
    setBusy(true);
    setCompileErrors([]);
    try {
      const result = await compileStudioCanvas(canvas);
      setYamlPreview(result.yaml);
      setStatus("Validated");
      return result.yaml;
    } catch (err) {
      const errors = (err as Error & { compile_errors?: StudioCompileError[] }).compile_errors || [];
      setCompileErrors(errors);
      setStatus(err instanceof Error ? err.message : "Validation failed");
      return null;
    } finally {
      setBusy(false);
    }
  }, [canvas]);

  const save = React.useCallback(async () => {
    setBusy(true);
    setCompileErrors([]);
    try {
      await saveStudioCanvas(canvas.id, canvas);
      setStatus("Saved");
      if (playbookId === "new") {
        router.replace(`/playbooks/studio/${encodeURIComponent(canvas.id)}`);
      }
    } catch (err) {
      const errors = (err as Error & { compile_errors?: StudioCompileError[] }).compile_errors || [];
      setCompileErrors(errors);
      setStatus(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }, [canvas, playbookId, router]);

  const run = React.useCallback(async () => {
    setBusy(true);
    setCompileErrors([]);
    try {
      const result = await compileStudioCanvas(canvas);
      const initial_state = Object.fromEntries(
        (canvas.variables || []).map((variable) => {
          const current = variable.default ?? "";
          const entered = window.prompt(`Value for ${variable.name}`, String(current));
          return [variable.name, entered ?? current];
        }),
      );
      const runResult = await startPlaybookRun({
        graph_id: String(result.yaml.id || canvas.id),
        initial_state,
        steps: result.yaml.steps as Array<Record<string, unknown>>,
        edges: result.yaml.edges as Array<Record<string, unknown>>,
        entry: typeof result.yaml.entry === "string" ? result.yaml.entry : undefined,
      });
      router.push(`/playbooks/${runResult.run_id}`);
    } catch (err) {
      const errors = (err as Error & { compile_errors?: StudioCompileError[] }).compile_errors || [];
      setCompileErrors(errors);
      setStatus(err instanceof Error ? err.message : "Run failed");
    } finally {
      setBusy(false);
    }
  }, [canvas, router]);

  const publish = React.useCallback(async (options?: {
    scope?: "personal" | "org";
    note?: string;
    require_scout_approval?: boolean;
  }) => {
    setBusy(true);
    try {
      await saveStudioCanvas(canvas.id, canvas);
      const result = await publishStudioPlaybook(canvas.id, options);
      setStatus(`Published ${result.version_hash.slice(0, 12)}`);
      setVersions(await listStudioVersions(canvas.id));
    } catch (err) {
      const errors = (err as Error & { compile_errors?: StudioCompileError[] }).compile_errors || [];
      setCompileErrors(errors);
      setStatus(err instanceof Error ? err.message : "Publish failed");
    } finally {
      setBusy(false);
    }
  }, [canvas]);

  const exportYaml = React.useCallback(async () => {
    const yaml = await validate();
    if (!yaml) return;
    const blob = new Blob([JSON.stringify(yaml, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${canvas.id}.yaml`;
    link.click();
    URL.revokeObjectURL(url);
  }, [canvas.id, validate]);

  const importYaml = React.useCallback(async (yaml: string) => {
    const payload = await importYamlPlaybook(yaml);
    setCanvas(payload.canvas);
    setStatus("Imported YAML");
  }, []);

  const importN8n = React.useCallback(async (workflow: Record<string, unknown>) => {
    const payload = await importN8nWorkflow(workflow);
    setCanvas(payload.canvas);
    setStatus(payload.warnings.length ? payload.warnings.join("; ") : "Imported n8n workflow");
  }, []);

  const invalidNodeIds = React.useMemo(
    () => new Set(compileErrors.map((error) => error.node_id).filter(Boolean) as string[]),
    [compileErrors],
  );

  return {
    canvas,
    setCanvas,
    selectedNodeId,
    setSelectedNodeId,
    selectedNode: canvas.nodes.find((node) => node.id === selectedNodeId) || null,
    compileErrors,
    invalidNodeIds,
    yamlPreview,
    versions,
    loading,
    busy,
    status,
    onNodesChange,
    onEdgesChange,
    updateNode,
    save,
    run,
    validate,
    publish,
    exportYaml,
    importYaml,
    importN8n,
    readOnly: Boolean(runId),
    autoLayout: () => setCanvas((current) => autoLayoutCanvas(current)),
  };
}
