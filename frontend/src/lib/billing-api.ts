import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

export type BillingStatus = {
  enabled: boolean;
  provider?: string;
  product_id?: string;
  product_name?: string;
  trial_days?: number;
  plans?: BillingPlan[];
};

export type BillingPrice = {
  amount: number;
  currency: string;
  interval: "month" | "year" | null;
  discount_text?: string | null;
};

export type BillingPlan = {
  id: string;
  name: string;
  description: string;
  prices: BillingPrice[];
  seats: number;
  metadata: Record<string, unknown>;
  feature_flags: Record<string, unknown>;
};

export type BillingSubscription = {
  plan_id?: string;
  status?: string;
  trial_ends_at?: string | null;
  current_period_end?: string | null;
  cancel_at_period_end?: boolean;
  seats?: number;
  feature_flags?: Record<string, unknown>;
};

export type BillingAccount = {
  product: { id: string; name: string; trial_days?: number } | null;
  subscription: BillingSubscription | null;
  customer: Record<string, unknown> | null;
  feature_matrix: Record<string, Record<string, unknown>>;
  plans?: BillingPlan[];
};

export type BillingInvoice = {
  id: string;
  number?: string;
  status?: string;
  total?: number;
  currency?: string;
  created_at?: string;
  html_body?: string;
  pdf_url?: string;
};

export type BillingSeat = {
  id: string;
  email: string;
  role: string;
  status?: string;
};

export type WalletStatus = {
  workspace_id: string;
  hosted?: boolean;
  policy?: {
    deployment_mode?: string;
    plan_id?: string;
    managed_ai_available?: boolean;
    byok_default?: boolean;
    included_credits_monthly?: number;
    trial_credits?: number;
    trial_daily_cap_credits?: number;
  };
  wallet?: {
    balance_credits?: number;
    included_remaining?: number;
    available_credits?: number;
    trial_granted?: number;
  };
  daily_credits_used?: number;
  daily_cap?: number | null;
  low_credit?: boolean;
  exhausted?: boolean;
  byok_available?: boolean;
  actions_when_exhausted?: string[];
};

export class BillingApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "BillingApiError";
    this.status = status;
  }
}

async function handleResponse<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new BillingApiError(parseApiErrorMessage(payload, fallback), response.status);
  }
  return response.json() as Promise<T>;
}

export function isBillingGateError(error: unknown): boolean {
  if (typeof error === "string") {
    return /Feature not available on current plan/i.test(error);
  }
  if (error instanceof BillingApiError) {
    return error.status === 402;
  }
  if (error instanceof Error) {
    return /Feature not available on current plan/i.test(error.message);
  }
  return false;
}

export function billingGateFeatureName(error: unknown): string | null {
  const message =
    typeof error === "string"
      ? error
      : error instanceof Error
        ? error.message
        : null;
  if (!message) return null;
  const match = message.match(/Feature not available on current plan:\s*(.+)/i);
  return match?.[1]?.trim() || null;
}

export async function fetchBillingStatus(): Promise<BillingStatus> {
  const response = await ceApi("/api/billing/status");
  return handleResponse<BillingStatus>(response, "Failed to load billing status");
}

export async function fetchBillingAccount(): Promise<BillingAccount> {
  const response = await ceApi("/api/billing/portal/account");
  return handleResponse<BillingAccount>(response, "Failed to load billing account");
}

export async function fetchBillingInvoices(): Promise<BillingInvoice[]> {
  const response = await ceApi("/api/billing/portal/invoices");
  const data = await handleResponse<{ items: BillingInvoice[] }>(response, "Failed to load invoices");
  return data.items || [];
}

export async function fetchBillingInvoice(id: string): Promise<BillingInvoice> {
  const response = await ceApi(`/api/billing/portal/invoices/${encodeURIComponent(id)}`);
  return handleResponse<BillingInvoice>(response, "Failed to load invoice");
}

export async function startCheckout(
  planId: string,
  interval: "month" | "year" = "month",
): Promise<{ checkout_url: string }> {
  const response = await ceApi("/api/billing/portal/checkout", {
    method: "POST",
    body: JSON.stringify({ plan_id: planId, interval }),
  });
  return handleResponse<{ checkout_url: string }>(response, "Failed to start checkout");
}

export async function startTrial(
  planId: string,
  interval: "month" | "year" = "month",
): Promise<{ mode: string; checkout_url?: string; subscription?: BillingSubscription }> {
  const response = await ceApi("/api/billing/portal/trial", {
    method: "POST",
    body: JSON.stringify({ plan_id: planId, interval }),
  });
  return handleResponse(response, "Failed to start trial");
}

export async function upgradePlan(
  planId: string,
  interval: "month" | "year" = "month",
): Promise<{ checkout_url: string }> {
  const response = await ceApi("/api/billing/portal/upgrade", {
    method: "POST",
    body: JSON.stringify({ plan_id: planId, interval }),
  });
  return handleResponse<{ checkout_url: string }>(response, "Failed to upgrade plan");
}

export async function cancelSubscription(atPeriodEnd = true): Promise<void> {
  const response = await ceApi("/api/billing/portal/cancel", {
    method: "POST",
    body: JSON.stringify({ at_period_end: atPeriodEnd }),
  });
  await handleResponse(response, "Failed to cancel subscription");
}

export async function resumeSubscription(): Promise<void> {
  const response = await ceApi("/api/billing/portal/resume", { method: "POST" });
  await handleResponse(response, "Failed to resume subscription");
}

export async function openPaymentMethodPortal(): Promise<{ portal_url: string }> {
  const response = await ceApi("/api/billing/portal/payment-method", { method: "POST" });
  return handleResponse<{ portal_url: string }>(response, "Failed to open payment portal");
}

export async function fetchSeats(): Promise<BillingSeat[]> {
  const response = await ceApi("/api/billing/portal/seats");
  const data = await handleResponse<{ items: BillingSeat[] }>(response, "Failed to load seats");
  return data.items || [];
}

export async function inviteSeat(email: string, role = "member"): Promise<BillingSeat> {
  const response = await ceApi("/api/billing/portal/seats/invite", {
    method: "POST",
    body: JSON.stringify({ email, role }),
  });
  const data = await handleResponse<{ seat: BillingSeat }>(response, "Failed to invite seat");
  return data.seat;
}

export async function removeSeat(seatId: string): Promise<void> {
  const response = await ceApi(`/api/billing/portal/seats/${encodeURIComponent(seatId)}`, {
    method: "DELETE",
  });
  await handleResponse(response, "Failed to remove seat");
}

export async function redirectToCheckout(planId: string, interval: "month" | "year" = "month"): Promise<void> {
  const { checkout_url } = await startCheckout(planId, interval);
  window.location.href = checkout_url;
}

export async function redirectToPaymentPortal(): Promise<void> {
  const { portal_url } = await openPaymentMethodPortal();
  window.location.href = portal_url;
}

export async function fetchWalletStatus(): Promise<WalletStatus> {
  const response = await ceApi("/api/billing/wallet/status");
  return handleResponse<WalletStatus>(response, "Failed to load AI wallet status");
}

export type BillingCatalogEntry = {
  label: string;
  price_id: string;
  amount: number | null;
  currency: string;
  interval: "month" | "year" | null;
};

export type BillingAdminPlan = {
  id: string;
  name: string;
  description?: string;
  prices: BillingPrice[];
};

export async function fetchBillingAdminCatalog(): Promise<{ items: BillingCatalogEntry[]; count: number }> {
  const response = await ceApi("/api/billing/admin/catalog");
  return handleResponse(response, "Failed to load Stripe price catalog");
}

export async function fetchBillingAdminPricing(): Promise<{
  config_path: string;
  product: { id: string; name: string; trial_days?: number };
  plans: BillingAdminPlan[];
}> {
  const response = await ceApi("/api/billing/admin/pricing");
  return handleResponse(response, "Failed to load plan pricing");
}

export async function saveBillingAdminPricing(body: {
  plans: Array<{
    id: string;
    prices: Array<{ interval: "month" | "year"; stripe_price_id: string | null }>;
  }>;
}): Promise<{ ok: boolean; config_path: string }> {
  const response = await ceApi("/api/billing/admin/pricing", {
    method: "PUT",
    body: JSON.stringify(body),
  });
  return handleResponse(response, "Failed to save plan pricing");
}

export async function createDonationCheckout(
  amountGbp: number,
  donationId = "coffee",
): Promise<{
  checkout_url: string;
  session_id: string;
  donation: {
    id: string;
    name: string;
    amount: number;
    amount_gbp: number;
    currency: string;
    pricing: string;
  };
}> {
  const response = await ceApi("/api/billing/donation/checkout", {
    method: "POST",
    body: JSON.stringify({ amount_gbp: amountGbp, donation_id: donationId }),
  });
  return handleResponse(response, "Failed to start donation checkout");
}
