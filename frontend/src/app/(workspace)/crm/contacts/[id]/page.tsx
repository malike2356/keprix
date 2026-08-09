"use client";

import Typography from "@mui/material/Typography";
import { useParams } from "next/navigation";
import useSWR from "swr";
import CrmDetailEditor from "@/components/crm/CrmDetailEditor";
import { CRM_WORKSPACE, type CrmRecord } from "@/components/crm/types";
import { fetchCrmRecord } from "@/lib/crm-api";

export default function CrmContactDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const detail = useSWR(id ? ["crm-contact", CRM_WORKSPACE, id] : null, () =>
    fetchCrmRecord("contacts", id, CRM_WORKSPACE),
  );

  if (detail.isLoading && !detail.data) {
    return <Typography color="text.secondary">Loading contact...</Typography>;
  }

  const record = detail.data?.record as CrmRecord | undefined;
  if (!record) {
    return (
      <Typography color="text.secondary">
        Contact not found.{" "}
        <Typography component="a" href="/crm/contacts" color="primary" sx={{ textDecoration: "underline" }}>
          Back to contacts
        </Typography>
      </Typography>
    );
  }

  return (
    <CrmDetailEditor
      kind="contacts"
      record={record}
      backHref="/crm/contacts"
      backLabel="All contacts"
      onSaved={() => void detail.mutate()}
      fields={[
        { key: "display_name", label: "Display name" },
        { key: "email", label: "Email" },
        { key: "source", label: "Source" },
        { key: "assigned_agent", label: "Assigned agent" },
        { key: "tags", label: "Tags (comma separated)" },
      ]}
    />
  );
}
