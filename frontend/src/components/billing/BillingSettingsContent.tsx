"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid2";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import BillingCheckoutBanner from "@/components/billing/BillingCheckoutBanner";
import BillingDisabledState from "@/components/billing/BillingDisabledState";
import BillingInvoiceTable from "@/components/billing/BillingInvoiceTable";
import BillingPlanCard from "@/components/billing/BillingPlanCard";
import BillingPlanCompare from "@/components/billing/BillingPlanCompare";
import BillingSeatsPanel from "@/components/billing/BillingSeatsPanel";
import BillingSubscriptionSummary from "@/components/billing/BillingSubscriptionSummary";
import AgentAppUsageCard from "@/components/agent-apps/AgentAppUsageCard";
import type { BillingInterval, CheckoutBannerState } from "@/components/billing/billing-types";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonStatGrid, SkeletonTable } from "@/components/ui/loading";
import {
  cancelSubscription,
  fetchBillingAccount,
  fetchBillingInvoice,
  fetchBillingInvoices,
  fetchBillingStatus,
  fetchSeats,
  inviteSeat,
  redirectToCheckout,
  redirectToPaymentPortal,
  removeSeat,
  resumeSubscription,
  startTrial,
  upgradePlan,
} from "@/lib/billing-api";

export default function BillingSettingsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [interval, setInterval] = React.useState<BillingInterval>("month");
  const [actionLoading, setActionLoading] = React.useState(false);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [checkoutBanner, setCheckoutBanner] = React.useState<CheckoutBannerState | null>(null);

  const { data: status, isLoading: statusLoading } = useSWR("billing-status", fetchBillingStatus);
  const billingEnabled = status?.enabled === true;

  const { data: account, mutate: mutateAccount, isLoading: accountLoading } = useSWR(
    billingEnabled ? "billing-account" : null,
    fetchBillingAccount,
  );
  const { data: invoices, mutate: mutateInvoices, isLoading: invoicesLoading } = useSWR(
    billingEnabled ? "billing-invoices" : null,
    fetchBillingInvoices,
  );
  const seatsIncluded = account?.subscription?.seats ?? 1;
  const showSeats = seatsIncluded > 1;
  const { data: seats, mutate: mutateSeats, isLoading: seatsLoading } = useSWR(
    billingEnabled && showSeats ? "billing-seats" : null,
    fetchSeats,
  );

  React.useEffect(() => {
    const checkout = searchParams.get("checkout");
    if (checkout === "success" || checkout === "cancel") {
      setCheckoutBanner(checkout);
      if (checkout === "success") {
        void mutateAccount();
        void mutateInvoices();
      }
      router.replace("/settings/billing");
    }
  }, [searchParams, router, mutateAccount, mutateInvoices]);

  const plans = account?.plans || [];
  const currentPlanId = account?.subscription?.plan_id || null;
  const currentPlan = plans.find((plan) => plan.id === currentPlanId) || null;
  const hasSubscription = Boolean(account?.subscription);
  const hasPaidPrices = plans.some((plan) => plan.prices?.some((price) => price.amount > 0));

  const refreshAll = async () => {
    await Promise.all([mutateAccount(), mutateInvoices(), showSeats ? mutateSeats() : Promise.resolve()]);
  };

  const runAction = async (action: () => Promise<void>) => {
    setActionLoading(true);
    setActionError(null);
    try {
      await action();
      await refreshAll();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Billing action failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartTrial = (planId: string) =>
    runAction(async () => {
      await startTrial(planId);
    });

  const handleSubscribe = (planId: string, selectedInterval: BillingInterval) =>
    runAction(async () => {
      if (hasSubscription) {
        const { checkout_url } = await upgradePlan(planId, selectedInterval);
        window.location.href = checkout_url;
        return;
      }
      await redirectToCheckout(planId, selectedInterval);
    });

  const handleViewInvoice = async (invoiceId: string) => {
    try {
      const invoice = await fetchBillingInvoice(invoiceId);
      if (invoice.pdf_url) {
        window.open(invoice.pdf_url, "_blank", "noopener,noreferrer");
        return;
      }
      if (invoice.html_body) {
        const blob = new Blob([invoice.html_body], { type: "text/html" });
        const url = URL.createObjectURL(blob);
        window.open(url, "_blank", "noopener,noreferrer");
        window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to open invoice");
    }
  };

  if (statusLoading) {
    return (
      <Box>
        <SkeletonStatGrid count={2} />
        <Box sx={{ mt: 2 }}>
          <SkeletonTable rows={4} columns={5} />
        </Box>
      </Box>
    );
  }

  if (!billingEnabled) {
    return <BillingDisabledState />;
  }

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Self-hosted OSS deployments can ignore this page. It applies when SaaS billing is enabled for this instance.
      </Typography>

      <BillingCheckoutBanner state={checkoutBanner} onDismiss={() => setCheckoutBanner(null)} />

      {actionError ? (
        <Alert severity="error" onClose={() => setActionError(null)} sx={{ mb: 2 }}>
          {actionError}
        </Alert>
      ) : null}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <BillingSubscriptionSummary
            plan={currentPlan}
            subscription={account?.subscription || null}
            productName={account?.product?.name || status?.product_name}
            trialDays={account?.product?.trial_days ?? status?.trial_days}
            loading={accountLoading}
            onCancel={() => runAction(() => cancelSubscription(true))}
            onResume={() => runAction(() => resumeSubscription())}
            actionLoading={actionLoading}
          />
        </Grid>

        <Grid size={{ xs: 12, lg: 6 }}>
          <DashboardCard title="Payment method" subtitle="Update card and billing details in Stripe">
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Payment methods are managed securely through Stripe Customer Portal.
            </Typography>
            <Button variant="outlined" onClick={() => runAction(() => redirectToPaymentPortal())} disabled={actionLoading}>
              Manage payment method
            </Button>
          </DashboardCard>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1, flexWrap: "wrap", gap: 1 }}>
            <Typography variant="h6">Plans</Typography>
            {hasPaidPrices ? (
              <ToggleButtonGroup
                size="small"
                exclusive
                value={interval}
                onChange={(_event, value: BillingInterval | null) => {
                  if (value) setInterval(value);
                }}
              >
                <ToggleButton value="month">Monthly</ToggleButton>
                <ToggleButton value="year">Yearly</ToggleButton>
              </ToggleButtonGroup>
            ) : null}
          </Box>
          <Grid container spacing={2}>
            {plans.map((plan) => (
              <Grid key={plan.id} size={{ xs: 12, md: 4 }}>
                <BillingPlanCard
                  plan={plan}
                  interval={interval}
                  currentPlanId={currentPlanId}
                  hasSubscription={hasSubscription}
                  trialDays={account?.product?.trial_days ?? status?.trial_days}
                  loading={actionLoading}
                  onStartTrial={handleStartTrial}
                  onSubscribe={handleSubscribe}
                />
              </Grid>
            ))}
          </Grid>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <AgentAppUsageCard />
        </Grid>

        <Grid size={{ xs: 12 }}>
          <BillingPlanCompare plans={plans} featureMatrix={account?.feature_matrix || {}} />
        </Grid>

        <Grid size={{ xs: 12 }}>
          <BillingInvoiceTable
            invoices={invoices || []}
            loading={invoicesLoading}
            onViewInvoice={handleViewInvoice}
          />
        </Grid>

        {showSeats ? (
          <Grid size={{ xs: 12 }}>
            <BillingSeatsPanel
              seats={seats || []}
              seatsIncluded={seatsIncluded}
              loading={seatsLoading}
              actionLoading={actionLoading}
              onInvite={async (email, role) => {
                await inviteSeat(email, role);
                await mutateSeats();
              }}
              onRemove={async (seatId) => {
                await removeSeat(seatId);
                await mutateSeats();
              }}
            />
          </Grid>
        ) : null}
      </Grid>
    </Box>
  );
}
