import { ceApi } from "@/lib/ce-api";

export type UiNavItem = {
  id: string;
  label: string;
  href: string;
  group: string;
  icon: string;
};

export type UiContract = {
  product: string;
  terminology_version: string;
  navigation: {
    groups: Array<{ id: string; label: string }>;
    items: UiNavItem[];
  };
  statuses: Record<string, { label: string; role: string }>;
  actions: Array<{ id: string; label: string; href?: string; action?: string; surface: string[] }>;
  approvals: {
    fields: string[];
    risk_levels: string[];
    actions: { approve: string; reject: string };
  };
  empty_states: Record<string, { title: string; description: string }>;
  forms?: Record<string, Array<Record<string, string>>>;
  tables?: Record<string, Array<Record<string, string>>>;
  errors: Record<string, string>;
  agent: {
    status: string;
    label: string;
    current_job: string | null;
    awaiting_approval: boolean;
  };
  workspace: {
    id: string;
    name: string;
    user: string;
    role: string;
  };
  feature_flags: Record<string, boolean>;
};

let cachedContract: UiContract | null = null;

export async function fetchUiContract(): Promise<UiContract> {
  const response = await ceApi("/api/ui/contract");
  if (!response.ok) {
    throw new Error("Failed to load UI contract");
  }
  const data = (await response.json()) as UiContract;
  cachedContract = data;
  return data;
}

export function getCachedUiContract(): UiContract | null {
  return cachedContract;
}
