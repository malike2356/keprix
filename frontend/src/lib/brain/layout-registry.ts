import { applyForceLayout, applyForceLayoutSync } from "@/lib/brain/layout-force";
import { applyHierarchicalLayout } from "@/lib/brain/layout-hierarchical";
import { applyRadialLayout } from "@/lib/brain/layout-radial";
import { applyTemporalLayout } from "@/lib/brain/layout-temporal";
import type { LayoutFn, LayoutInput, LayoutMode, LayoutPositions } from "@/lib/brain/layout-types";

export type LayoutDefinition = {
  id: LayoutMode;
  label: string;
  apply: LayoutFn;
};

export const LAYOUT_REGISTRY: LayoutDefinition[] = [
  { id: "force", label: "Force", apply: (input) => applyForceLayout(input.nodes, input.edges) },
  { id: "temporal", label: "Time", apply: async (input) => applyTemporalLayout(input) },
  { id: "radial", label: "Radial", apply: async (input) => applyRadialLayout(input) },
  { id: "hierarchical", label: "Hierarchy", apply: async (input) => applyHierarchicalLayout(input) },
];

export function getLayoutDefinition(mode: LayoutMode): LayoutDefinition {
  return LAYOUT_REGISTRY.find((layout) => layout.id === mode) ?? LAYOUT_REGISTRY[0];
}

export function applyLayout(mode: LayoutMode, input: LayoutInput): Promise<LayoutPositions> {
  const layout = getLayoutDefinition(mode);
  // Defer to the next task so the browser can paint the busy spinner before the
  // synchronous layout computation blocks the main thread.
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      try {
        resolve(layout.apply(input));
      } catch (err) {
        reject(err);
      }
    }, 0);
  });
}

export function applyLayoutSync(mode: LayoutMode, input: LayoutInput): LayoutPositions {
  if (mode === "force") return applyForceLayoutSync(input.nodes, input.edges);
  if (mode === "temporal") return applyTemporalLayout(input);
  if (mode === "radial") return applyRadialLayout(input);
  return applyHierarchicalLayout(input);
}

const STORAGE_PREFIX = "brain-graph-layout";

export function layoutStorageKey(workspaceId: string): string {
  return `${STORAGE_PREFIX}-${workspaceId}`;
}

export function readLayoutPreference(workspaceId: string): LayoutMode {
  if (typeof window === "undefined") return "force";
  const raw = window.localStorage.getItem(layoutStorageKey(workspaceId));
  if (raw === "temporal" || raw === "radial" || raw === "hierarchical" || raw === "force") {
    return raw;
  }
  return "force";
}

export function writeLayoutPreference(workspaceId: string, mode: LayoutMode): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(layoutStorageKey(workspaceId), mode);
}

const CLUSTER_PREFIX = "brain-graph-clusters";

export function clustersStorageKey(workspaceId: string): string {
  return `${CLUSTER_PREFIX}-${workspaceId}`;
}

export function readClustersPreference(workspaceId: string): boolean {
  if (typeof window === "undefined") return true;
  const raw = window.localStorage.getItem(clustersStorageKey(workspaceId));
  if (raw === "0") return false;
  if (raw === "1") return true;
  return true;
}

export function writeClustersPreference(workspaceId: string, enabled: boolean): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(clustersStorageKey(workspaceId), enabled ? "1" : "0");
}
