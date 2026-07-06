const CURRENCY_LOCALE: Record<string, string> = {
  gbp: "en-GB",
  usd: "en-US",
  eur: "de-DE",
};

export function formatMoneyMinorUnits(amount: number, currency = "gbp"): string {
  const code = currency.toUpperCase();
  const locale = CURRENCY_LOCALE[currency.toLowerCase()] || "en-GB";
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: code,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount / 100);
}

export function formatBillingInterval(interval: string | null | undefined): string {
  if (interval === "year") return "year";
  if (interval === "month") return "month";
  return "";
}

export function formatFeatureValue(value: unknown): string {
  if (value === true) return "Yes";
  if (value === false) return "No";
  if (value === null || value === undefined) return "-";
  return String(value);
}

export function formatBillingDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function daysUntil(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const target = new Date(iso).getTime();
  if (Number.isNaN(target)) return null;
  const diff = target - Date.now();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}
