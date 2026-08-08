"use client";

import CrmCollectionPage from "@/components/crm/CrmCollectionPage";

export default function CrmDealsPage() {
  return (
    <CrmCollectionPage
      kind="deals"
      title="Deals"
      description="Opportunities toward customer and paying stages. Paying promotion stays Soft Wall gated."
      createFields={[
        { key: "name", label: "Deal name", required: true },
        { key: "source", label: "Source" },
        { key: "account_id", label: "Account id (optional)" },
      ]}
      buildCreateBody={(draft) => ({
        name: draft.name?.trim(),
        source: draft.source?.trim() || "manual",
        account_id: draft.account_id?.trim() || undefined,
        stage: "discovered",
      })}
      emptyMessage="No CRM deals yet. Create an opportunity above. No fake pipeline is seeded."
    />
  );
}
