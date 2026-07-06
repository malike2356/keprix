export type CostStatus = "estimated" | "unknown" | "included" | string;

export function formatTokenCount(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}k`;
  }
  return value.toLocaleString();
}

export function formatUsdCost(value: number | null | undefined, costStatus?: CostStatus): string {
  if (costStatus === "unknown" || value === null || value === undefined) {
    return "-";
  }
  if (costStatus === "included") {
    return "$0.00";
  }
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return "-";
  }
  if (Math.abs(amount) < 1) {
    return `$${amount.toFixed(4)}`;
  }
  return `$${amount.toFixed(2)}`;
}

export function costTooltip(costStatus?: CostStatus): string | undefined {
  if (costStatus === "unknown") {
    return "Pricing unavailable for this model";
  }
  if (costStatus === "included") {
    return "Included in subscription";
  }
  return undefined;
}

export function formatRecordedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}
