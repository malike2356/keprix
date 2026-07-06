"use client";

import Box from "@mui/material/Box";
import * as React from "react";
import BillingSettingsContent from "@/components/billing/BillingSettingsContent";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonDetailPanel } from "@/components/ui/loading";

export default function BillingSettingsPage() {
  return (
    <Box>
      <PageHeader title="Billing and subscription" description="Manage your plan, payment method, and invoices." />
      <React.Suspense
        fallback={
          <Box sx={{ py: 2 }}>
            <SkeletonDetailPanel fields={5} />
          </Box>
        }
      >
        <BillingSettingsContent />
      </React.Suspense>
    </Box>
  );
}
