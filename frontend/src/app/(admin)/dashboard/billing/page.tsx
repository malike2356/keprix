"use client";

import Box from "@mui/material/Box";
import * as React from "react";
import BillingSettingsContent from "@/components/billing/BillingSettingsContent";
import PageContainer from "@/components/shared/PageContainer";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import { useRequireAdmin } from "@/lib/ce-auth";

export default function AdminBillingPage() {
  useRequireAdmin();

  return (
    <PageContainer
      title="Billing"
      description="Manage your plan, payment method, and invoices."
      padded={false}
    >
      <React.Suspense
        fallback={
          <Box sx={{ py: 2 }}>
            <SkeletonDetailPanel fields={5} />
          </Box>
        }
      >
        <BillingSettingsContent />
      </React.Suspense>
    </PageContainer>
  );
}
