"use client";

import CrmCollectionPage from "@/components/crm/CrmCollectionPage";

export default function CrmContactsPage() {
  return (
    <CrmCollectionPage
      kind="contacts"
      title="Contacts"
      description="People with contact channels. Consent and contactability deepen in later prompts."
      createFields={[
        { key: "display_name", label: "Display name", required: true },
        { key: "email", label: "Email" },
        { key: "source", label: "Source" },
      ]}
      buildCreateBody={(draft) => ({
        display_name: draft.display_name?.trim(),
        email: draft.email?.trim() || undefined,
        source: draft.source?.trim() || "manual",
        stage: "discovered",
      })}
      emptyMessage="No CRM contacts yet. Create a person above. No fake contacts are seeded."
    />
  );
}
