import { ceApi } from "@/lib/ce-api";

export type Edition = "community" | "enterprise";

export type EditionInfo = {
  edition: Edition;
  features: Record<string, boolean>;
};

export async function fetchEdition(): Promise<EditionInfo> {
  const response = await ceApi("/api/licensing/edition");
  if (!response.ok) {
    throw new Error("Failed to load edition");
  }
  return response.json();
}

export function isFeatureEnabled(info: EditionInfo | undefined, feature: string): boolean {
  return Boolean(info?.features?.[feature]);
}
