"use client";

import CrmCollectionPage from "@/components/crm/CrmCollectionPage";

export default function CrmAccountsPage() {
  return (
    <CrmCollectionPage
      kind="accounts"
      title="Accounts"
      description="Companies and organisations in the workspace CRM."
      createFields={[
        { key: "name", label: "Account name", required: true },
        { key: "domain", label: "Domain" },
        { key: "company_number", label: "Company number" },
        { key: "source", label: "Source" },
      ]}
      buildCreateBody={(draft) => ({
        name: draft.name?.trim(),
        domain: draft.domain?.trim() || undefined,
        company_number: draft.company_number?.trim() || undefined,
        source: draft.source?.trim() || "manual",
        stage: "discovered",
      })}
      emptyMessage="No CRM accounts yet. Create an organisation above. No demo companies are seeded."
      showCompanyAsName
    />
  );
}
