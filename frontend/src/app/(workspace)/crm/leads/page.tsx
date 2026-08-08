"use client";

import CrmCollectionPage from "@/components/crm/CrmCollectionPage";

export default function CrmLeadsPage() {
  return (
    <CrmCollectionPage
      kind="leads"
      title="Leads"
      description="CRM leads for review, Soft Wall enroll, and stage promotion. Empty until you create or import records."
      createFields={[
        { key: "name", label: "Name", required: true },
        { key: "email", label: "Email" },
        { key: "company_name", label: "Company" },
        { key: "source", label: "Source" },
      ]}
      buildCreateBody={(draft) => ({
        name: draft.name?.trim(),
        company_name: draft.company_name?.trim() || undefined,
        email: draft.email?.trim() || undefined,
        source: draft.source?.trim() || "manual",
        stage: "discovered",
      })}
      emptyMessage="No CRM leads yet. Create one above or wait for discovery/enrich jobs. No demo companies are seeded."
    />
  );
}
