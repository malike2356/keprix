import { ceApi } from "@/lib/ce-api";

export type SimplifiedModeConfig = {
  simplified_mode: boolean;
  hide_terminal_coding: boolean;
  documents_read_only: boolean;
  allowed_paths: string[];
};

export async function fetchSimplifiedMode(): Promise<SimplifiedModeConfig> {
  const response = await ceApi("/api/agent-os/simplified-mode");
  if (!response.ok) throw new Error("Failed to load simplified mode");
  return (await response.json()) as SimplifiedModeConfig;
}

export async function saveSimplifiedMode(body: SimplifiedModeConfig): Promise<SimplifiedModeConfig> {
  const response = await ceApi("/api/agent-os/simplified-mode", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as SimplifiedModeConfig;
}

export async function simplifiedModeGuard(path: string): Promise<{ blocked: boolean; redirect: string | null }> {
  const response = await ceApi(`/api/agent-os/simplified-mode/guard?path=${encodeURIComponent(path)}`);
  if (!response.ok) return { blocked: false, redirect: null };
  return (await response.json()) as { blocked: boolean; redirect: string | null };
}
