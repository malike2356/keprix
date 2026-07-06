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

export async function startTrial(planId: string): Promise<BillingAccount> {
  const response = await ceApi("/api/billing/portal/trial", {
    method: "POST",
    body: JSON.stringify({ plan_id: planId }),
  });
  const data = await handleResponse<{ subscription: BillingSubscription }>(response, "Failed to start trial");
  const account = await fetchBillingAccount();
  return { ...account, subscription: data.subscription };
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
