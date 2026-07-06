"use client";

import Alert from "@mui/material/Alert";
import type { CheckoutBannerState } from "@/components/billing/billing-types";

type BillingCheckoutBannerProps = {
  state: CheckoutBannerState | null;
  onDismiss: () => void;
};

export default function BillingCheckoutBanner({ state, onDismiss }: BillingCheckoutBannerProps) {
  if (!state) return null;

  if (state === "success") {
    return (
      <Alert severity="success" onClose={onDismiss} sx={{ mb: 2 }}>
        Payment successful. Your subscription will update shortly.
      </Alert>
    );
  }

  return (
    <Alert severity="info" onClose={onDismiss} sx={{ mb: 2 }}>
      Checkout was cancelled. You can choose a plan below when you are ready.
    </Alert>
  );
}
