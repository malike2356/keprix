import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type GuiModuleStatus = "available" | "partial" | "cli_api" | string;

export type GuiModule = {
  id: string;
  name: string;
  description: string;
  module: string;
  version: string;
  gui_href: string | null;
  gui_status: GuiModuleStatus;
  category: string;
};

export type ModulesCatalog = {
  installed_version: string;
  modules: GuiModule[];
  missing_gui: GuiModule[];
  counts: {
    total: number;
    available: number;
    partial: number;
    cli_api: number;
  };
  registry_versions?: string[];
};

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return (await response.json()) as T;
}

export async function fetchModulesCatalog(): Promise<ModulesCatalog> {
  return parseJson(await ceApi("/api/keprix/upgrade/modules"), "Failed to load modules catalog");
}

export function formatModuleCategory(category: string): string {
  if (!category) return "Other";
  return category
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatModuleStatus(status: GuiModuleStatus): string {
  switch (status) {
    case "available":
      return "Available";
    case "partial":
      return "Partial UI";
    case "cli_api":
      return "CLI / API";
    default:
      return String(status).replace(/_/g, " ");
  }
}

export function moduleStatusColor(
  status: GuiModuleStatus,
): "success" | "warning" | "default" | "info" {
  switch (status) {
    case "available":
      return "success";
    case "partial":
      return "warning";
    case "cli_api":
      return "default";
    default:
      return "info";
  }
}
