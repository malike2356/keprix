"use client";

import CrmCollectionPage from "@/components/crm/CrmCollectionPage";

export default function CrmListsPage() {
  return (
    <CrmCollectionPage
      kind="lists"
      title="Lists"
      description="Named lead and contact sets for Soft Wall review and enroll."
      createFields={[
        { key: "name", label: "List name", required: true },
        { key: "description", label: "Description" },
        { key: "source", label: "Source" },
      ]}
      buildCreateBody={(draft) => ({
        name: draft.name?.trim(),
        description: draft.description?.trim() || undefined,
        source: draft.source?.trim() || "manual",
      })}
      emptyMessage="No CRM lists yet. Create a list above to start review sets. No demo audiences are seeded."
    />
  );
}
