import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type PromoRedemption = {
  workspace_id: string;
  code: string;
  promo_id: string | null;
  amount_off: number;
  redeemed_at: string;
  order_id: string;
};

export async function fetchPromoRedemptions(): Promise<{ items: PromoRedemption[]; count: number; totals: Record<string, number> }> {
  const response = await ceApi("/api/billing/admin/promo/redemptions");
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseApiErrorMessage(payload, "Failed to load promo redemptions"));
  }
  return response.json();
}
