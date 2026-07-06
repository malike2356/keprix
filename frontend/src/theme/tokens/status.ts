import statusTokens from "../../../../ui/design-system/tokens/status.json";

type StatusToken = { label: string; role: string };

export const statusLabels = Object.fromEntries(
  Object.entries(statusTokens as Record<string, StatusToken>).map(([key, entry]) => [key, entry.label]),
) as Record<keyof typeof statusTokens, string>;

export type StatusKey = keyof typeof statusTokens;

const roleToChipColor: Record<string, "default" | "primary" | "secondary" | "success" | "warning" | "error" | "info"> = {
  muted: "default",
  info: "info",
  primary: "primary",
  warning: "warning",
  danger: "error",
  success: "success",
};

export const statusColors: Record<StatusKey, "default" | "primary" | "secondary" | "success" | "warning" | "error" | "info"> =
  Object.fromEntries(
    Object.entries(statusTokens as Record<string, StatusToken>).map(([key, entry]) => [
      key,
      roleToChipColor[entry.role] || "default",
    ]),
  ) as Record<StatusKey, "default" | "primary" | "secondary" | "success" | "warning" | "error" | "info">;

export function normalizeStatusKey(value: string): StatusKey {
  const key = value.replace(/-/g, "_").toLowerCase();
  if (key in statusLabels) {
    return key as StatusKey;
  }
  return "draft";
}
